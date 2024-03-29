"""EpiSim37 utilities."""

from pathlib import Path
from typing import Any

import h5py as h5
import polars as pl

from .parse_tree import mk_pt
from .ast1 import mk_ast1
from .codegen_cpu import (
    mk_ir as mk_cpu_ir,
    do_prepare as do_prepare_cpu,
    do_build as do_build_cpu,
    do_simulate as do_simulate_cpu,
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


class CPUSimulator:
    """Simulate on CPU."""

    def __init__(
        self,
        simulation_file: str | Path,
        work_dir: str | Path,
    ):
        self.simulation_file = Path(simulation_file)
        self.work_dir = Path(work_dir)

        assert self.simulation_file.exists(), "Simulation file doesn't exist"

        self.pt = mk_pt(str(self.simulation_file), self.simulation_file.read_bytes())
        self.ast1 = mk_ast1(self.simulation_file, self.pt)
        self.ir = mk_cpu_ir(self.ast1)

        self.ntm = NodeTableMeta.from_source_cpu(self.ir)
        self.etm = EdgeTableMeta.from_source_cpu(self.ir)

        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.gen_code_dir = self.work_dir / "gen_code"
        self.gen_code_dir.mkdir(parents=True, exist_ok=True)

    def __getstate__(self):
        return (self.simulation_file, self.work_dir)

    def __setstate__(self, d):
        (self.simulation_file, self.work_dir) = d

        self.pt = mk_pt(str(self.simulation_file), self.simulation_file.read_bytes())
        self.ast1 = mk_ast1(self.simulation_file, self.pt)
        self.ir = mk_cpu_ir(self.ast1)

        self.ntm = NodeTableMeta.from_source_cpu(self.ir)
        self.etm = EdgeTableMeta.from_source_cpu(self.ir)

        self.gen_code_dir = self.work_dir / "gen_code"

    def prepare_build(self) -> None:
        do_prepare_cpu(self.gen_code_dir, self.simulation_file, self.ir)

    def build(self) -> None:
        do_build_cpu(self.gen_code_dir)


class Simulation:
    def __init__(
        self,
        simulator: CPUSimulator,
        node_file: str | Path,
        edge_file: str | Path,
        input_file: str | Path,
    ):
        self.simulator = simulator
        self.node_file = Path(node_file)
        self.edge_file = Path(edge_file)
        self.input_file = Path(input_file)

        assert self.node_file.exists(), "Node file doesn't exist"
        assert self.edge_file.exists(), "Edge file doesn't exist"

    def prepare_input(self) -> None:
        do_prepare_input(
            self.simulator.ntm,
            self.simulator.etm,
            self.node_file,
            self.edge_file,
            self.input_file,
        )

    def simulate(
        self,
        output_file: str | Path,
        num_ticks: int = 0,
        configs: dict[str, Any] = {},
        verbose: bool = False,
    ) -> None:
        output_file = Path(output_file)
        do_simulate_cpu(
            self.simulator.gen_code_dir,
            input_file=self.input_file,
            output_file=output_file,
            num_ticks=num_ticks,
            configs=configs,
            verbose=verbose,
        )

    def extract_nodes(self) -> pl.DataFrame:
        assert self.input_file.exists(), "Input file doesn't exist."
        return do_read_nodes_df(self.input_file, self.simulator.ntm)

    def extract_edges(self) -> pl.DataFrame:
        assert self.input_file.exists(), "Input file doesn't exist."
        return do_read_edges_df(self.input_file, self.simulator.etm)

    def num_nodes(self) -> int:
        with h5.File(self.input_file, "r") as fobj:
            return fobj.attrs["num_nodes"].item()  # type: ignore

    def num_edges(self) -> int:
        with h5.File(self.input_file, "r") as fobj:
            return fobj.attrs["num_edges"].item()  # type: ignore

    def extract_summary(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        contagion = find_contagion(contagion_name, self.simulator.ast1)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_summary(sim_output, contagion)
        return df

    def extract_transitions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        contagion = find_contagion(contagion_name, self.simulator.ast1)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_transitions(sim_output, contagion)
        return df

    def extract_interventions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        contagion = find_contagion(contagion_name, self.simulator.ast1)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_interventions(sim_output, contagion)
        return df

    def extract_transmissions(
        self, output_file: str | Path, contagion_name: str = ""
    ) -> pl.DataFrame:
        output_file = Path(output_file)
        contagion = find_contagion(contagion_name, self.simulator.ast1)
        with h5.File(output_file, "r") as sim_output:
            df = do_extract_transmissions(sim_output, contagion)
        return df
