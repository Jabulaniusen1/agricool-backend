import time

from django.contrib.auth.models import Group

from base.apps.user.models import User, ServiceProvider, Company, Farmer

from base.apps.storage.models import Location, CropType

from base.apps.security.management.commands.load_roles import Command as loadRoleCommand

from model_bakery import baker
import random

dummy_data = {
    "email": "@testing.com",
    "password": "Testing@123",
    "first_name": "testing-first-name",
    "last_name": "testing-last-name",
    "phone": "+9170",
    "name": "testing-name",
}

client_types = ("farmer", "operator", "service_provider")
crop_names = [
    "Tomato",
    "Corn",
    "Potato",
    "Carrot",
    "Lettuce",
    "Cucumber",
    "Strawberry",
    "Pumpkin",
    "Bean",
    "Pepper",
]


#  setup
def seed(*args):
    """
    Required dummies
    """
    if "location" in args:

        company = Company.objects.first()

        if not company:
            get_client("service_provider")
            company = Company.objects.first()

        Location.objects.create(
            name=dummy_data["name"], company=company, latitude="100", longitude="100"
        )

    if "crop-type" in args:
        for crop_name in crop_names:
            CropType.objects.create(name=crop_name)


# # TODO : teardown
def purge():
    CropType.objects.all().delete()
    Location.objects.all().delete()


def clean_client():
    User.objects.all().delete()
    ServiceProvider.objects.all().delete()
    Company.objects.all().delete()


def get_client(type):
    """
    Get a type User
    """
    if type not in client_types:
        raise Exception("Use Type Not Specified")

    random_number = "".join(str(random.randint(0, 9)) for _ in range(8))

    user = User.objects.create_user(
        email=f'{type}.{str(time.time())}{dummy_data["email"]}',
        password=dummy_data["password"],
        phone=f'{dummy_data["phone"]}{random_number}',
        first_name=dummy_data["first_name"],
        last_name=dummy_data["last_name"],
        gender="ma",
        language="en",
    )

    company = None

    if type == "service_provider":
        company = Company.objects.create(name=type + str(time.time()), country="IN")

        ServiceProvider.objects.create(company=company, user=user)

    farmer = None
    if type == "farmer":
        farmer = Farmer.objects.create(user=user, smartphone=True)
        farmer.companies.add(company)

    return user


class DummyFactory:

    def __init__(self):

        failure_count = 0
        while not Group.objects.filter(name="ServiceProvider").exists():
            # using while to see something

            loadRoleCommand().handle(dry_run=False)

            print("groups created -->>>>>>", failure_count)
            failure_count += 1

            groups = Group.objects.all()

            print(len(groups))

            # print(Group.objects.get(name="ServiceProvider"))

        service_provider_role = Group.objects.get(name="ServiceProvider")

        # op_role = Group.objects.get(name='Operator')

        self.user_company = get_client("service_provider")
        service_provider_role.user_set.add(self.user_company)

        self.company = self.user_company.service_provider.company

        self.user_operator = baker.make(
            "user.Operator", company=self.company, make_m2m=True
        )
        # op_role.user_set.add(self.user_operator)

        self.location = baker.make("storage.Location", company=self.company)

        self.cooling_unit = baker.make(
            "storage.CoolingUnit",
            operators=[self.user_operator.user],
            location=self.location,
            _fill_optional=True,
            food_capacity_in_metric_tons=float(random.randint(1, 400)),
            capacity_in_metric_tons=float(random.randint(1, 400)),
            capacity_in_number_crates=random.randint(1, 400),
        )

        self.user_farmer = baker.make(
            "user.Farmer",
            cooling_units=[self.cooling_unit],
            companies=[self.company],
            make_m2m=True,
        )

        self.crop = baker.make("storage.Crop", crop_type=baker.make("storage.CropType"))

        pricing = baker.make("storage.Pricing", _fill_optional=True)

        baker.make(
            "storage.CoolingUnitCrop",
            crop=self.crop,
            cooling_unit=self.cooling_unit,
            pricing=pricing,
        )
