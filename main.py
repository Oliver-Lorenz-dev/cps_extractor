from argparser import Parser
from blastn import Blast
from annotation import Annotation


def main(args):
    blast = Blast(args.reference, args.query, args.hit_length)

    blast_results = blast.parse_blast_results(blast.run_blastn())

    final_results = blast.compare_blast_dicts(blast_results)

    sorted_results = blast.sort_and_reverse_complement_hits(final_results)

    sequence = blast.curate_sequence(sorted_results)

    blast.write_fasta(sequence, args.output)

    blast_results_dev = blast.parse_blast_results_dev(blast.run_blastn())

    print(blast_results_dev)

    Annotator = Annotation(args.output, args.training_file)

    Annotator.run_bakta()

    sample_name = args.output.split(".fa")[0]
    out_dir = str()
    if "/" in sample_name:
        out_dir = sample_name.rsplit('/', 1)[0]
        sample_name = sample_name.split("/")[-1]

    cds_gff = Annotator.get_cds_annotations(
        f"{sample_name}.gff3", f"{sample_name}_cds.gff3"
    )

    cds_fna = Annotator.get_cds_fna(
        cds_gff, f"{sample_name}.fna", f"{sample_name}_cds.fna"
    )

    mutations = Annotator.find_mutations(cds_fna)
    if out_dir != str():
        Annotator.write_disruptive_mutations_file(f"{out_dir}/{sample_name}_mutations.csv", mutations)
    else:
        Annotator.write_disruptive_mutations_file(f"{sample_name}_mutations.csv", mutations)


if __name__ == "__main__":
    args = Parser.parse_args(vargs=None)
    main(args)
