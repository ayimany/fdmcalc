import argparse
import os

from pydantic import BaseModel, ValidationError

YEAR_IN_HOURS = 8766
HOUR_IN_SECONDS = 3600

class CalculatorData(BaseModel):
    material_used_grams: float
    material_cost_per_kg: float
    energy_cost_per_kWh: float
    machine_preheat_time_seconds: float
    machine_preheat_kWh: float
    machine_operating_time_hours: float
    machine_operating_kWh: float
    machine_cost_purchase: float
    machine_lifespan_years: float
    machine_repair_percentage: float
    operator_job_hours: float
    operator_wage_hourly: float
    shipping_cost: float
    margin_percentage: float
    taxes_percentage: float

    def material_cost(self) -> float:
        return self.material_cost_per_kg / 1000.0 * self.material_used_grams

    def energy_cost(self) -> float:
        return self.energy_cost_per_kWh * (
                (self.machine_preheat_time_seconds / HOUR_IN_SECONDS) * self.machine_preheat_kWh +
                self.machine_operating_time_hours * self.machine_operating_kWh
        )

    def wear_cost(self) -> float:
        return (
            (self.machine_cost_purchase
             * (1 + self.machine_repair_percentage)
             * self.machine_operating_time_hours)
            / (YEAR_IN_HOURS * self.machine_lifespan_years)
        )

    def labor_cost(self) -> float:
        return self.operator_job_hours * self.operator_wage_hourly

    def total_process_cost(self):
        return (
            self.material_cost()
            + self.energy_cost()
            + self.wear_cost()
            + self.labor_cost()
        )

    # TODO: don't reuse the same function thrice
    def margin_gain(self):
        return self.total_process_cost() * self.margin_percentage

    def tax_addition(self):
        return (self.total_process_cost() + self.margin_gain() + self.shipping_cost) * self.taxes_percentage

    def total_cost(self) -> float:
        return self.total_process_cost() + self.margin_gain() + self.tax_addition()

class CalculatorOutput(BaseModel):
    material_cost: float
    energy_cost: float
    wear_cost: float
    labor_cost: float
    shipping_cost: float
    margin_gain: float
    tax_addition: float
    total_cost: float


def dump_variable_template(filename: str):
    zero = CalculatorData(material_used_grams = 0,
                          material_cost_per_kg = 0,
                          energy_cost_per_kWh = 0,
                          machine_preheat_time_seconds = 0,
                          machine_preheat_kWh = 0,
                          machine_operating_time_hours= 0,
                          machine_operating_kWh = 0,
                          machine_cost_purchase = 0,
                          machine_lifespan_years = 0,
                          machine_repair_percentage= 0,
                          operator_job_hours = 0,
                          operator_wage_hourly = 0,
                          shipping_cost = 0,
                          margin_percentage= 0,
                          taxes_percentage= 0,
                          )

    try:
        with open(filename, "w") as f:
            f.write(zero.model_dump_json())
    except IOError as e:
        print("Error while exporting template:", e)

    print(f"Exported template to {filename}")



def main():
    did_something = False

    parser = argparse.ArgumentParser()
    parser.add_argument("--import", dest="import_file")
    parser.add_argument("--export", dest="export_file",)
    parser.add_argument("--dump-template", action="store_true")
    args = parser.parse_args()

    if args.dump_template:
        dump_variable_template("fdmcalc_template.json")
        did_something = True

    if args.import_file is not None:
        did_something = True

        if not os.path.exists(args.import_file):
            print(f"File {args.export} does not exist.")
            exit(1)

        try:
            with open(args.import_file, "rb+") as f:
                data = CalculatorData.model_validate_json(f.read())
        except ValidationError as e:
            print(f"Error while parsing {args.export}: {e}")
            exit(1)

        if data.machine_lifespan_years == 0:
            print(f"Error: Cannot use a machine lifespan of zero years.")
            exit(1)

        costs = CalculatorOutput(material_cost = data.material_cost(),
                                 energy_cost = data.energy_cost(),
                                 wear_cost = data.wear_cost(),
                                 labor_cost = data.labor_cost(),
                                 shipping_cost = data.shipping_cost,
                                 margin_gain = data.margin_gain(),
                                 tax_addition = data.tax_addition(),
                                 total_cost = data.total_cost()
                                 )

        costs_json = costs.model_dump_json()

        if args.export_file is not None:
            try:
                with open(args.export_file, "w") as f:
                    f.write(costs_json)
            except Exception as e:
                print(f"Error while writing to {args.export_file}: {e}")
                exit(1)
        else:
            print(costs_json)

    if not did_something:
        print("* Use the --import flag to import machine, material and process information in JSON format.")
        print("* Use the --dump-template flag to export a template example filled with zeroes.")


if __name__ == '__main__':
    main()