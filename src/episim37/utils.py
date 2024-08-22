"""EpiSim37 utilities."""

from pathlib import Path
from typing import Any

import h5py as h5
import polars as pl
import jinja2

from .parse_tree import mk_pt
from .ast import mk_ast
from .check_ast import check_ast
from .codegen_openmp import (
    do_prepare as do_prepare_openmp,
    do_build as do_build_openmp,
    do_simulate as do_simulate_openmp,
)
from .input_helpers import (
    NodeTableMeta,
    EdgeTableMeta,
    do_prepare_input,
    do_read_edges_df,
    do_read_nodes_df,
)
from .output_helpers import (
    do_extract_summary,
    do_extract_transitions,
    do_extract_interventions,
    do_extract_transmissions,
    find_contagion,
)

ENVIRONMENT = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class OpenMPSimulator:
    """Simulate on CPU."""

    def __init__(
        self, simulation_file: str | Path, work_dir: str | Path, **template_kwargs
    ):
        self.simulation_file = Path(simulation_file)
        self.work_dir = Path(work_dir)

        assert self.simulation_file.exists(), "Simulation file doesn't exist"

        self.work_dir.mkdir(parents=True, exist_ok=True)

        if template_kwargs:
            sim_template = ENVIRONMENT.from_string(self.simulation_file.read_text())
            sim_rendered = sim_template.render(**template_kwargs)
        else:
            sim_rendered = self.simulation_file.read_text()

        self.rendered_simulation_file = self.work_dir / "simulator.esl37"
        if self.rendered_simulation_file.exists():
            exisiting_sim_rendered = self.rendered_simulation_file.read_text()
        else:
            exisiting_sim_rendered = ""

        if exisiting_sim_rendered != sim_rendered:
            self.rendered_simulation_file.write_text(sim_rendered)

        self.pt = mk_pt(
            str(self.rendered_simulation_file),
            self.rendered_simulation_file.read_bytes(),
        )
        self.ast = mk_ast(self.rendered_simulation_file, self.pt)
        check_ast(self.ast)

        self.ntm = NodeTableMeta.from_source(self.ast.node_table)
        self.etm = EdgeTableMeta.from_source(self.ast.edge_table)

    def __getstate__(self):
        return (self.simulation_file, self.work_dir)

    def __setstate__(self, d):
        (self.simulation_file, self.work_dir) = d

        self.rendered_simulation_file = self.work_dir / "simulator.esl37"

        self.pt = mk_pt(
            str(self.rendered_simulation_file),
            self.rendered_simulation_file.read_bytes(),
        )
        self.ast = mk_ast(self.rendered_simulation_file, self.pt)
        check_ast(self.ast)

        self.ntm = NodeTableMeta.from_source(self.ast.node_table)
        self.etm = EdgeTableMeta.from_source(self.ast.edge_table)

    def prepare_build(self) -> None:
        do_prepare_openmp(self.work_dir, self.rendered_simulation_file, self.ast)

    def build(self) -> None:
        do_build_openmp(self.work_dir)

    def prepare_input(
        self, node_file: str | Path, edge_file: str | Path, input_file: str | Path
    ) -> None:
        node_file = Path(node_file)
        edge_file = Path(edge_file)
        input_file = Path(input_file)

        assert node_file.exists(), "Node file doesn't exist"
        assert edge_file.exists(), "Edge file doesn't exist"

        do_prepare_input(
            self.ntm,
            self.etm,
            node_file,
            edge_file,
            input_file,
        )

    def extract_nodes(self, input_file: str | Path) -> pl.DataFrame:
        input_file = Path(input_file)
        assert input_file.exists(), "Input file doesn't exist"
        return do_read_nodes_df(input_file, self.ntm)

    def extract_edges(self, input_file: str | Path) -> pl.DataFrame:
        input_file = Path(input_file)
        assert input_file.exists(), "Input file doesn't exist"
        return do_read_edges_df(input_file, self.etm)

    def num_nodes(self, input_file: str | Path) -> int:
        input_file = Path(input_file)
        assert input_file.exists(), "Input file doesn't exist"
        with h5.File(input_file, "r") as fobj:
            return fobj.attrs["num_nodes"].item()  # type: ignore

    def num_edges(self, input_file: str | Path) -> int:
        input_file = Path(input_file)
        assert input_file.exists(), "Input file doesn't exist"
        with h5.File(input_file, "r") as fobj:
            return fobj.attrs["num_edges"].item()  # type: ignore

    def simulate(
        self,
        input_file: str | Path,
        output_file: str | Path,
        num_ticks: int = 0,
        configs: dict[str, Any] = {},
        verbose: bool = False,
    ) -> None:
        input_file = Path(input_file)
        assert input_file.exists(), "Input file doesn't exist"

        output_file = Path(output_file)

        do_simulate_openmp(
            self.work_dir,
            input_file=input_file,
            output_file=output_file,
            num_ticks=num_ticks,
            configs=configs,
            verbose=verbose,
        )

    def extract_summary(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        assert output_file.exists(), "Output file doesn't exist"
        contagion = find_contagion(contagion_name, self.ast)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_summary(sim_output, contagion)
        return df

    def extract_transitions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        assert output_file.exists(), "Output file doesn't exist"
        contagion = find_contagion(contagion_name, self.ast)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_transitions(sim_output, contagion)
        return df

    def extract_interventions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        assert output_file.exists(), "Output file doesn't exist"
        contagion = find_contagion(contagion_name, self.ast)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_interventions(sim_output, contagion)
        return df

    def extract_transmissions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        assert output_file.exists(), "Output file doesn't exist"
        contagion = find_contagion(contagion_name, self.ast)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_transmissions(sim_output, contagion)
        return df

    def num_ticks(self, output_file: str | Path) -> int:
        output_file = Path(output_file)
        assert output_file.exists(), "Output file doesn't exist"
        with h5.File(output_file, "r") as fobj:
            return fobj.attrs["num_ticks"].item()  # type: ignore
