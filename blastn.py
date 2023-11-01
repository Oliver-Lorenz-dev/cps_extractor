import subprocess
import xml.etree.ElementTree as ET
import logging
import datetime

logging.basicConfig(
    filename=f"cps_extractor_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M').replace(' ','-')}_blast.log",
    encoding="utf-8",
    level=logging.INFO,
)


class Blast:
    def __init__(self, ref: str, query: str):
        self.ref = ref
        self.query = query

    def run_blastn(self) -> str:
        query_basename = self.query.split(".f")[0]
        blast_output_file = f"{query_basename}_blast_results.xml"
        blastn_cmd = f"blastn -query {self.query} -db {self.ref} -out {query_basename}_blast_results.xml -outfmt 5"
        subprocess.check_output(blastn_cmd, shell=True)
        return blast_output_file

    def parse_blast_results(self, blast_xml_file: str) -> list:
        blast_results = list()

        tree = ET.parse(blast_xml_file)
        root = tree.getroot()

        for query in root.findall(".//Iteration"):
            query_id = query.find(".//Iteration_query-def").text

            for hit in query.findall(".//Hit"):
                hit_length = int(hit.find(".//Hit_len").text)
                hit_def = hit.find(".//Hit_def").text
                if int(hit_length) >= 5000:
                    for hsp in hit.findall(".//Hsp"):
                        q_sequence = hsp.find(".//Hsp_qseq").text
                        hit_start = int(hsp.find(".//Hsp_hit-from").text)
                        hit_end = int(hsp.find(".//Hsp_hit-to").text)
                        aln_len = hsp.find(".//Hsp_align-len").text
                        if hit_start < hit_end:
                            seq_length = int(hit_end) - int(hit_start)
                        else:
                            seq_length = int(hit_start) - int(hit_end)
                        hit_frame = hsp.find(".//Hsp_hit-frame").text
                        if int(aln_len) >= 5000:
                            blast_result = {
                                "hit_start": hit_start,
                                "hit_end": hit_end,
                                "hit_frame": int(hit_frame),
                                "seq_length": seq_length,
                                "query_id": query_id,
                                "hit_def": hit_def,
                                "seq": q_sequence,
                            }

                            blast_results.append(blast_result)
        return blast_results

    def do_dicts_overlap(self, dict1: dict, dict2: dict) -> bool:
        # check if one blast sequence is entirely contained in a larger hit
        overlap = False
        if int(dict1["seq_length"]) > int(dict2["seq_length"]):
            if int(dict1["hit_start"]) < int(dict1["hit_end"]) and int(
                dict2["hit_start"]
            ) < int(dict2["hit_end"]):
                if int(dict2["hit_start"]) > int(dict1["hit_start"]) and int(
                    dict2["hit_end"]
                ) < int(dict1["hit_end"]):
                    overlap = True
        return overlap

    def get_largest_hit(self, final_blast_results: list) -> str:
        max_seq_length = 0
        for result in final_blast_results:
            seq_length = int(result["seq_length"])
            if seq_length > max_seq_length:
                max_seq_length = seq_length
                max_hit_def = result["hit_def"]
        return max_hit_def

    def compare_blast_dicts(self, blast_results: list) -> list:
        overlaps = list()

        # get the longest hit, remove hits from other references in the blastdb
        largest_hit_ref = self.get_largest_hit(blast_results)
        blast_results = [
            item for item in blast_results if item["hit_def"] == largest_hit_ref
        ]

        # check for any sequences that are contained entirely by larger hits and remove them
        for i in range(len(blast_results)):
            for j in range(i + 1, len(blast_results)):
                dict1 = blast_results[i]
                dict2 = blast_results[j]
                if self.do_dicts_overlap(dict1, dict2):
                    if int(dict1["seq_length"]) > int(dict2["seq_length"]):
                        overlaps.append(dict2)
                    else:
                        overlaps.append(dict1)

        final_results = [item for item in blast_results if item not in overlaps]
        logging.info(final_results)
        return final_results

    def check_partial_overlap(self, dict1: dict, dict2: dict) -> bool:
        # check if one sequence partially overlaps another sequence
        overlap = False
        if int(dict1["hit_end"]) >= int(dict2["hit_start"]):
            overlap = True
        return overlap

    def reverse_complement(self, sequence: str) -> str:
        # rev comp, keep gaps as they are
        complement = {"A": "T", "T": "A", "C": "G", "G": "C", "-": "-"}
        reversed_sequence = sequence[::-1]
        reverse_complement_sequence = "".join(
            [complement[base] for base in reversed_sequence]
        )
        return reverse_complement_sequence

    def sort_and_reverse_complement_hits(self, blast_hits_dict: list) -> list:
        # sort hits based on start position, remove gaps and rev comp if needed
        for i in range(0, len(blast_hits_dict)):
            # rev comp if needed
            if blast_hits_dict[i]["hit_frame"] == -1:
                end = blast_hits_dict[i]["hit_start"]
                start = blast_hits_dict[i]["hit_end"]
                rc = self.reverse_complement(blast_hits_dict[i]["seq"])
                blast_hits_dict[i]["hit_start"] = start
                blast_hits_dict[i]["hit_end"] = end
                blast_hits_dict[i]["seq"] = rc

        # sort the data list on start pos
        sorted_data = sorted(blast_hits_dict, key=lambda x: x["hit_start"])
        return sorted_data

    def curate_sequence(self, sorted_data: list) -> str:
        # curate blast sequence from final blast results
        # if sequences don't overlap, join them together
        # if sequences do overlap, prioritise the match from the sequence with the higher length in overlapping regions
        seq = str()
        if len(sorted_data) == 0:
            logging.error("No blast hits found, please check the blast XML file")
            raise SystemExit(1)
        elif len(sorted_data) == 1:
            seq = sorted_data[0]["seq"]
        else:
            for i in range(0, (len(sorted_data) - 1)):
                if i == 0:
                    if self.check_partial_overlap(sorted_data[i], sorted_data[i + 1]):
                        if int(sorted_data[i]["seq_length"]) > int(
                            sorted_data[i + 1]["seq_length"]
                        ):
                            seq += sorted_data[i]["seq"]
                            overlap_index = (
                                1
                                + int(sorted_data[i]["hit_end"])
                                - int(sorted_data[i + 1]["hit_start"])
                            )
                            seq += sorted_data[i + 1]["seq"][overlap_index::]
                        else:
                            seq += sorted_data[i]["seq"][
                                0 : int((sorted_data[i + 1]["hit_start"]) - 1)
                            ]
                            seq += sorted_data[i + 1]["seq"]
                    else:
                        seq += sorted_data[i]["seq"]
                        seq += sorted_data[i + 1]["seq"]
                else:
                    if self.check_partial_overlap(sorted_data[i], sorted_data[i + 1]):
                        if int(sorted_data[i]["seq_length"]) > int(
                            sorted_data[i + 1]["seq_length"]
                        ):
                            overlap_index = (
                                1
                                + int(sorted_data[i]["hit_end"])
                                - int(sorted_data[i + 1]["hit_start"])
                            )
                            seq += sorted_data[i + 1]["seq"][overlap_index::]
                        else:
                            overlap_index = (
                                1
                                + int(sorted_data[i]["hit_end"])
                                - int(sorted_data[i + 1]["hit_start"])
                            )
                            seq = seq[:-overlap_index]
                            seq += sorted_data[i + 1]["seq"]

                    else:
                        seq += sorted_data[i + 1]["seq"]

        # remove gaps
        seq = seq.replace("-", "")
        return seq

    def write_fasta(self, sequence: str, output_file: str):
        fasta_output = output_file.split(".")[0]
        print(f"seq:{sequence}")
        with open(output_file, "w") as fasta:
            fasta.write(f">{fasta_output}\n")
            fasta.write(sequence)

    def parse_blast_results_dev(self, blast_xml_file: str) -> list:
        blast_results = list()

        tree = ET.parse(blast_xml_file)
        root = tree.getroot()

        for query in root.findall(".//Iteration"):
            query_id = query.find(".//Iteration_query-def").text

            for hit in query.findall(".//Hit"):
                hit_length = int(hit.find(".//Hit_len").text)
                hit_def = hit.find(".//Hit_def").text
                if int(hit_length) >= 5000:
                    for hsp in hit.findall(".//Hsp"):
                        q_sequence = hsp.find(".//Hsp_qseq").text
                        hit_start = int(hsp.find(".//Hsp_hit-from").text)
                        hit_end = int(hsp.find(".//Hsp_hit-to").text)
                        aln_len = hsp.find(".//Hsp_align-len").text
                        if hit_start < hit_end:
                            seq_length = int(hit_end) - int(hit_start)
                        else:
                            seq_length = int(hit_start) - int(hit_end)
                        hit_frame = hsp.find(".//Hsp_hit-frame").text
                        if int(aln_len) >= 5000:
                            blast_result = {
                                "hit_start": hit_start,
                                "hit_end": hit_end,
                                "hit_frame": int(hit_frame),
                                "seq_length": seq_length,
                                "query_id": query_id,
                                "hit_def": hit_def,
                            }

                            blast_results.append(blast_result)
        logging.info(blast_results)
        return blast_results
