"""Declarative specification of the four Bernanke-Blanchard equations.

Coefficient names are `<var>_L<lag>` (lag 0 = contemporaneous), `const`, and dummy names. The order of
terms matches Stata's `cnsreg` output order, which is the order the authors' MATLAB code indexes.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Block:
    """A regressor with a set of lags (e.g. gw at lags 1..4)."""
    var: str
    lags: tuple[int, ...]

    def names(self) -> list[str]:
        return [f"{self.var}_L{k}" for k in self.lags]


@dataclass(frozen=True)
class EquationSpec:
    name: str
    dep: str
    blocks: tuple[Block, ...]
    constant: bool = True
    dummies: tuple[str, ...] = ()
    # names of blocks whose coefficients jointly sum to `restriction_value`
    restriction_blocks: tuple[str, ...] = ()
    restriction_value: float = 1.0
    # blocks reported with their own sum-of-coefficients / p-values in the summary table
    summary_blocks: tuple[str, ...] = field(default=())

    def regressors(self) -> list[str]:
        names = [n for b in self.blocks for n in b.names()]
        names += list(self.dummies)
        if self.constant:
            names.append("const")
        return names

    def restriction_names(self) -> list[str]:
        out = []
        for b in self.blocks:
            if b.var in self.restriction_blocks:
                out += b.names()
        return out


L1_4 = (1, 2, 3, 4)
L0_4 = (0, 1, 2, 3, 4)


def base_equations(covid_dummies: bool = True) -> dict[str, EquationSpec]:
    """The four equations. `covid_dummies=True` is the 'full-sample' wage equation."""
    wage = EquationSpec(
        "gw", "gw",
        (Block("gw", L1_4), Block("cf1", L1_4), Block("magpty", (1,)),
         Block("vu", L1_4), Block("diffcpicf", L1_4)),
        constant=True,
        dummies=("D2020Q2", "D2020Q3") if covid_dummies else (),
        restriction_blocks=("gw", "cf1"),
        summary_blocks=("gw", "cf1", "vu", "diffcpicf", "magpty"),
    )
    price = EquationSpec(
        "gcpi", "gcpi",
        (Block("magpty", (0,)), Block("gcpi", L1_4), Block("gw", L0_4), Block("grpe", L0_4),
         Block("grpf", L0_4), Block("shortage", L0_4)),
        constant=True,
        restriction_blocks=("gcpi", "gw"),
        summary_blocks=("gcpi", "gw", "grpe", "grpf", "shortage", "magpty"),
    )
    cf1 = EquationSpec(
        "cf1", "cf1",
        (Block("cf1", L1_4), Block("cf10", L0_4), Block("gcpi", L0_4)),
        constant=False,
        restriction_blocks=("cf1", "cf10", "gcpi"),
        summary_blocks=("cf1", "cf10", "gcpi"),
    )
    cf10 = EquationSpec(
        "cf10", "cf10",
        (Block("cf10", L1_4), Block("gcpi", L0_4)),
        constant=False,
        restriction_blocks=("cf10", "gcpi"),
        summary_blocks=("cf10", "gcpi"),
    )
    return {"gw": wage, "gcpi": price, "cf1": cf1, "cf10": cf10}
