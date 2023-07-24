use std::io::Write;

use chrono::Local;
use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;

use ncbi_compress::ncbi_compress::ncbi_compress::fasta_compress;
// pub mod ncbi_compress;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to the input fasta file
    #[arg(short, long)]
    input_fasta: String,

    /// Path to the output fasta file
    #[arg(short, long)]
    output_fasta: String,

    /// Path to the accession to taxid csv file
    /// At least one required
    #[arg(short, long, required = true)]
    accession_mapping_files: Vec<String>,

    /// Taxids to drop from the output
    #[arg(long)]
    taxids_to_drop: Vec<u64>,

    /// Scaled value for the minhash
    /// (default: 1000)
    #[arg(short, long, default_value = "1000")]
    scaled: u64,

    /// Kmer size for the minhash
    /// (default: 31)
    #[arg(short, long, default_value = "31")]
    k: u32,

    /// Seed for the minhash
    /// (default: 42)
    #[arg(long, default_value = "42")]
    seed: u64,

    /// Similarity threshold for the minhash
    /// (default: 0.6)
    /// (must be between 0 and 1)
    #[arg(short = 't', long, default_value = "0.6")]
    similarity_threshold: f64,

    /// Chunk size for the parallelization
    /// (default: 1000)
    #[arg(short, long, default_value = "10000")]
    chunk_size: usize,

    /// Branching factor for the tree
    /// (default: 1000)
    #[arg(short, long, default_value = "1000")]
    branch_factor: usize,
}


pub fn main() {
    Builder::new()
        .format(|buf, record| {
            writeln!(
                buf,
                "{} {}: {}",
                record.level(),
                Local::now().format("%Y-%m-%d %H:%M:%S%.3f"),
                record.args()
            )
        })
        .filter(None, LevelFilter::Info)
        .init();

    let args = Args::parse();

    fasta_compress(
        args.input_fasta,
        args.accession_mapping_files,
        args.output_fasta,
        args.taxids_to_drop,
        args.scaled,
        args.k,
        args.seed,
        args.similarity_threshold,
        args.chunk_size,
        args.branch_factor,
    );
}
