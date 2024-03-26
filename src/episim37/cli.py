"""Command line interface."""

import click

from .parse_tree import print_parse_tree
from .ast import print_ast
from .check_ast import print_checked_ast

from .codegen_openmp import codegen_openmp
from .language_server import language_server
# from .input_helpers import prepare_input, process_input
# from .output_helpers import process_output


@click.group()
def cli():
    """EpiSim37: Epidemic Simulations on Contact Networks"""


@cli.group()
def debug():
    """Debug ESL37 code."""


debug.add_command(print_parse_tree)
debug.add_command(print_ast)
debug.add_command(print_checked_ast)
# debug.add_command(print_cpu_ir)

cli.add_command(language_server)

cli.add_command(codegen_openmp)
# cli.add_command(prepare_input)
# cli.add_command(process_input)
# cli.add_command(process_output)
