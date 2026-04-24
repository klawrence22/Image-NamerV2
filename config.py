# Temporary config file so compilation and basic running can occur
import os

FILE_EXTENSION = ".jpg"
YEAR_DATES = ["1990", "2020", "2021", "2022", "2023", "2024"]
HOMEDIR = os.path.expanduser("~")
RUN = "dev"


class SI:
    dev_dir = HOMEDIR
    prod_dir = HOMEDIR


si = SI()
