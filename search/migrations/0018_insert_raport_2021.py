# Generated by Django 3.0.7 on 2021-06-11 09:09
import csv
import re

from django.db import migrations
from psycopg2.extras import NumericRange

CSV_FIELDS = (
    "class__name",
    "class__info",
    "class__subjects",
    "class__occupation",
    "school__name",
    "school__addr__street",
    "school__addr__building_nr",
    "school__addr__postcode",
    "school__addr__district",
    "school__addr__city",
    "_0",  # "school__addr__borough",
    "_00",  # "school__addr__county",
    "school__type",
    "school__status",
    "institution__name",
    "institution__city",
    "institution__supervisor__name",
    "institution__supervisor__city",
    "_1",
    "_2",
    "_3",
    "_4",
    "_5",
    "_6",
    "school__type",
)
PUBLIC_SCHOOL = "szkoła publiczna"
CLASS_INFO_REGEX = r"\[(\S+)\]\s(([\S-]*)|(.+))\s*\((\S+)\)"
LANGUAGE_REGEX = r"([a-z*]+)"


def load(apps, schema_editor):
    School = apps.get_model("search", "School")
    Address = apps.get_model("search", "Address")
    HighSchoolClass = apps.get_model("search", "HighSchoolClass")
    ExtendedSubject = apps.get_model("search", "ExtendedSubject")
    Language = apps.get_model("search", "Language")

    with open("csvs/raport_oddzialy_2021.csv", newline="") as csv_file:
        reader = csv.DictReader(csv_file, CSV_FIELDS)
        next(reader)  # Skip header line
        for row in reader:
            data = {}
            for field in CSV_FIELDS:
                # Build dicts from field path
                field_path = field.split("__")
                current_dict = data
                for key in field_path[:-1]:
                    current_dict = current_dict.setdefault(key, dict())

                current_dict[field_path[-1]] = row[field]

            # School creation
            school_data = data["school"]

            try:
                school = School.objects.get(school_name=school_data["name"])
            except School.DoesNotExist:
                address = Address.objects.filter(**school_data["addr"]).first()
                if not address:
                    address = Address.objects.create(**school_data["addr"])

                is_public = school_data["status"] == PUBLIC_SCHOOL
                school_extra_data = {}
                if not is_public:
                    school_extra_data = {
                        "is_public": school_data["status"],
                    }
                school = School.objects.create(
                    school_name=school_data["name"],
                    school_type=school_data["type"],
                    is_public=is_public,
                    data=school_extra_data,
                    address=address,
                )

            class_info = re.search(CLASS_INFO_REGEX, data["class"]["info"])

            # Class creation
            hsc = HighSchoolClass.objects.create(
                type=class_info.group(1),
                name=data["class"]["name"],
                school=school,
                year=NumericRange(2021, 2023, "[)"),
            )

            # Subjects assignment
            subjects = data["class"]["subjects"].split(",")
            subject_options = {
                name: short
                for short, name in ExtendedSubject._meta.get_field("name").choices
            }
            for subject in subjects:
                subject = subject.strip()
                name = subject_options.get(subject, None)
                if not name:
                    continue
                ExtendedSubject.objects.create(
                    name=name,
                    high_school_class=hsc,
                )

            # Languages assignment
            langs = re.compile(LANGUAGE_REGEX).findall(class_info.group(5))

            for i, lang in enumerate(langs):
                is_multiple_levels = lang.endswith("*")
                is_bilingual = hsc.type == "D" and i == 0
                name = lang.replace("*", "")
                nr = 1 if lang in subjects else 2
                Language.objects.create(
                    high_school_class=hsc,
                    name=name,
                    multiple_levels=is_multiple_levels,
                    is_bilingual=is_bilingual,
                    nr=nr,
                )


def reverse(apps, schema_editor):
    HighSchoolClass = apps.get_model("search", "HighSchoolClass")
    HighSchoolClass.objects.filter(year=(2021, 2023)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0017_auto_20210605_2206"),
    ]

    operations = [migrations.RunPython(load, reverse)]
