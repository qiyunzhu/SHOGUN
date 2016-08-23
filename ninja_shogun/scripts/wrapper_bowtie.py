#!/usr/bin/env python
import click

from ninja_shogun.wrappers import bowtie2_align


@click.command()
@click.argument('infile', type=click.Path(exists=True))
@click.argument('outfile', type=click.Path(exists=False))
@click.argument('database', type=click.Path(exists=True))
def bowtie2_wrapper(infile, outfile, database):
    print(bowtie2_align(infile, outfile, database))

if __name__ == '__main__':
    bowtie2_wrapper()
