
"""Sales report generator - processes regional sales data."""



REGIONS = ["north", "south", "east", "west"]



SALES_DATA = {

    "north": {"q1": 12400, "q2": 15200, "q3": 11800, "q4": 18900},

    "south": {"q1": 9800,  "q2": 10400, "q3": 12100, "q4": 14300},

    "east":  {"q1": 15600, "q2": 14900, "q3": 16200, "q4": 19400},

    "west":  {"q1": 8200,  "q2": 9100,  "q3": 8800},

}





def quarter_total(region_data, quarter):

    """Return sales for one quarter of one region."""

    return region_data[quarter]





def annual_total(region_name):

    """Sum all four quarters for a region."""

    region_data = SALES_DATA[region_name]

    total = 0

    for q in ["q1", "q2", "q3", "q4"]:

        total += quarter_total(region_data, q)

    return total





def build_report():

    """Build the full annual report across all regions."""

    report = {}

    for region in REGIONS:

        report[region] = annual_total(region)

    return report





if __name__ == "__main__":

    results = build_report()

    for region, total in results.items():

        print(f"{region}: {total}")

