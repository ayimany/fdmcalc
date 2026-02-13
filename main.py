import argparse
import json
import os
import sys
from functools import cached_property
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Constants
YEAR_IN_HOURS = 8766
HOUR_IN_SECONDS = 3600


class CalculatorInput(BaseModel):
    """Schema for FDM calculation input data."""
    model_config = ConfigDict(frozen=True)

    material_used_grams: float
    material_cost_per_kg: float
    energy_cost_per_kWh: float
    machine_preheat_time_seconds: float
    machine_preheat_kWh: float
    machine_operating_time_hours: float
    machine_operating_kWh: float
    machine_cost_purchase: float
    machine_lifespan_years: float = Field(gt=0)
    machine_repair_percentage: float
    operator_job_hours: float
    operator_wage_hourly: float
    shipping_cost: float
    margin_percentage: float
    taxes_percentage: float


class CalculatorOutput(BaseModel):
    """Schema for FDM calculation results."""
    material_cost: float
    energy_cost: float
    wear_cost: float
    labor_cost: float
    shipping_cost: float
    margin_gain: float
    tax_addition: float
    total_cost: float


class FDMCalculator:
    """Handles the business logic for FDM printing cost estimation."""

    def __init__(self, data: CalculatorInput):
        self.data = data

    @cached_property
    def material_cost(self) -> float:
        return (self.data.material_cost_per_kg / 1000.0) * self.data.material_used_grams

    @cached_property
    def energy_cost(self) -> float:
        preheat_hours = self.data.machine_preheat_time_seconds / HOUR_IN_SECONDS
        preheat_energy = preheat_hours * self.data.machine_preheat_kWh
        operating_energy = self.data.machine_operating_time_hours * self.data.machine_operating_kWh
        return self.data.energy_cost_per_kWh * (preheat_energy + operating_energy)

    @cached_property
    def wear_cost(self) -> float:
        total_lifespan_hours = YEAR_IN_HOURS * self.data.machine_lifespan_years
        total_machine_cost = self.data.machine_cost_purchase * (1 + self.data.machine_repair_percentage)
        return (total_machine_cost * self.data.machine_operating_time_hours) / total_lifespan_hours

    @cached_property
    def labor_cost(self) -> float:
        return self.data.operator_job_hours * self.data.operator_wage_hourly

    @cached_property
    def total_process_cost(self) -> float:
        return (
            self.material_cost
            + self.energy_cost
            + self.wear_cost
            + self.labor_cost
        )

    @cached_property
    def margin_gain(self) -> float:
        return self.total_process_cost * self.data.margin_percentage

    @cached_property
    def tax_addition(self) -> float:
        base_for_tax = self.total_process_cost + self.margin_gain + self.data.shipping_cost
        return base_for_tax * self.data.taxes_percentage

    @cached_property
    def total_cost(self) -> float:
        return self.total_process_cost + self.margin_gain + self.tax_addition

    def calculate(self) -> CalculatorOutput:
        return CalculatorOutput(
            material_cost=self.material_cost,
            energy_cost=self.energy_cost,
            wear_cost=self.wear_cost,
            labor_cost=self.labor_cost,
            shipping_cost=self.data.shipping_cost,
            margin_gain=self.margin_gain,
            tax_addition=self.tax_addition,
            total_cost=self.total_cost,
        )


def dump_template(filename: str, silent: bool = False):
    """Generates a template JSON file with default zero values."""
    # Create a template with reasonable default or zero values
    template_data = CalculatorInput(
        material_used_grams=0.0,
        material_cost_per_kg=0.0,
        energy_cost_per_kWh=0.0,
        machine_preheat_time_seconds=0.0,
        machine_preheat_kWh=0.0,
        machine_operating_time_hours=0.0,
        machine_operating_kWh=0.0,
        machine_cost_purchase=0.0,
        machine_lifespan_years=1.0,  # Avoid division by zero
        machine_repair_percentage=0.0,
        operator_job_hours=0.0,
        operator_wage_hourly=0.0,
        shipping_cost=0.0,
        margin_percentage=0.0,
        taxes_percentage=0.0,
    )

    try:
        with open(filename, "w") as f:
            f.write(template_data.model_dump_json(indent=4))
        if not silent:
            print(f"Exported template to {filename}")
    except IOError as e:
        print(f"Error while exporting template: {e}", file=sys.stderr)


def run_calculator(import_file: str, export_file: Optional[str] = None, silent: bool = False):
    """Loads data, performs calculation, and exports/prints results."""
    if not os.path.exists(import_file):
        print(f"Error: File {import_file} does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(import_file, "rb") as f:
            input_data = CalculatorInput.model_validate_json(f.read())
    except ValidationError as e:
        print(f"Error while parsing {import_file}:\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error reading {import_file}: {e}", file=sys.stderr)
        sys.exit(1)

    calculator = FDMCalculator(input_data)
    results = calculator.calculate()
    results_json = results.model_dump_json(indent=4 if export_file else None)

    if export_file:
        try:
            with open(export_file, "w") as f:
                f.write(results_json)
            if not silent:
                print(f"Results exported to {export_file}")
        except Exception as e:
            print(f"Error while writing to {export_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not silent:
            print(results_json)


def main():
    parser = argparse.ArgumentParser(description="FDM Printing Cost Calculator")
    parser.add_argument("--import", dest="import_file", help="Path to input JSON file")
    parser.add_argument("--export", dest="export_file", help="Path to save results (JSON)")
    parser.add_argument("--dump-template", action="store_true", help="Generate a template JSON file")
    parser.add_argument("--silent", action="store_true", help="Suppress all stdout output")

    args = parser.parse_args()

    if args.dump_template:
        dump_template("fdmcalc_template.json", silent=args.silent)
    elif args.import_file:
        run_calculator(args.import_file, args.export_file, silent=args.silent)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()