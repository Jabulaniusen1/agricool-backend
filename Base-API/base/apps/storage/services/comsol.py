import math
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta

from django.utils import timezone

from ..models import CoolingUnitSpecifications, Crate, Produce
from .ttpu import get_set_t

###
## Comsol / DTs fns
###
COMSOL_CSA_DIR = os.environ.get("COMSOL_CSA_DIR") or "/media/comsol/csa/"
COMSOL_PREFS_DIR = os.environ.get("COMSOL_PREFS_DIR") or "/media/comsol/prefs/"
COMSOL_SETUP_CONFIG = os.environ.get("COMSOL_SETUP_CONFIG") or "/media/comsol/setupconfig.ini"

def is_process_running(process_name):
    try:
        # Execute the ps command and grep for the process name
        result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, text=True)
        if process_name in result.stdout:
            return True
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

comsol_context_dir_base_path = "/tmp/comsol-context-folders"
def get_comsol_context_temp_dir():
    """
        Create random folders prefixed by the runtime date.

        Context: COMSOL models require a folder to read the initial values and
        the temperature table. The outputs will also be published within the
        same folder. This method allows the creation of trully random folders.

        Note: the logic calling this function should be responsible for a defer
        deletion system call of this folder in order to prevent storage
        accumulation.
    """
    # Ensure the base directory exists
    os.makedirs(comsol_context_dir_base_path, exist_ok=True)

    # Create a truly random temporary directory within the base directory
    temp_dir = tempfile.mkdtemp(prefix=(str(datetime.now())).replace(" ", ""), dir=comsol_context_dir_base_path)

    os.chmod(temp_dir, 0o777)

    return temp_dir

def comsol_compute(comsol_context_tmp, digital_twin_identifier, timeout=120):
    """
        Executes a COMSOL model against a folder
    """

    # Ensure Xvfb is running
    if not is_process_running('Xvfb'):
        print("Process Xvfb is now being initialized as it was not running...")
        display = os.environ.get('DISPLAY', ':0')
        subprocess.Popen(['Xvfb', display]) # we don't want to wait for the process
        # but lets wait for a second, just in case
        time.sleep(1)

    command = []

    # some crates have specific identifiers which needs to match the correct AI model. They are chosen here or defaulted to the generic one
    if digital_twin_identifier == "1":
        command.append(f"{COMSOL_CSA_DIR}/2022.05.02_DigitalTwinAppleV5.sh")
    elif digital_twin_identifier == "25":
        command.append(f"{COMSOL_CSA_DIR}/2022.05.02_DigitalTwinTomatoV5.sh")
    elif digital_twin_identifier == "22":
        command.append(f"{COMSOL_CSA_DIR}/2022.05.02_DigitalTwinPotatoV5.sh")
    elif digital_twin_identifier == "2":
        command.append(f"{COMSOL_CSA_DIR}/2022.05.02_DigitalTwinBananaV5.sh")
    else:
        command.append(f"{COMSOL_CSA_DIR}/2022.05.02_DigitalTwin_GenericV5.sh")

    # Run against the provided folder path
    command.append(f"-s \"{COMSOL_SETUP_CONFIG}\"")
    command.append(f"-prefsdir \"{COMSOL_PREFS_DIR}\"")
    command.append("-run")
    command.append("-appargnames arg1")
    command.append(f"-appargvalues \"'{comsol_context_tmp}/'\"")

    # run DT () based on index
    command = "".join(command)
    print(f"running comsol with command: {command}")

    # Start the subprocess
    proc = subprocess.Popen(command, shell=True)

    # Wait for the command to finish or timeout after an established timeout period
    try:
        proc.wait(timeout=timeout)  # Defaults to 120 seconds = 2 minutes
    except subprocess.TimeoutExpired:
        proc.kill()  # Kill the process if it takes longer than 120 seconds
        raise Exception(f"Command '{command}' timed out after {timeout} seconds")



def comsol_write_initial_values(
    comsol_context_tmp,
    crate,
    quality_dt=1, # Initial quality
    temperature_dt=290, # temperature - kelvin
    shelf_life_buffer=0.5, # shelf life buffer
    fruit_index=1, # fruit identifier
    last_temp=0.0 # last temperature in Celsius
):
    identifier = crate.produce.crop.digital_twin_identifier
    file = open(os.path.join(comsol_context_tmp, "InitialValues.txt"), "w")

    file.write(f"I0_sl \t{str(quality_dt)}\n")
    file.write(f"T_fruit_ini \t{str(temperature_dt)}\n")
    file.write(f"SL_buffer  \t{str(shelf_life_buffer)}\n")
    file.write(f"FruitIndex  \t{fruit_index}\n")
    file.write(f"T_set \t{round(float(last_temp))}") # perhaps needs to be changed to ambient temp

    file.close()

def comsol_write_input_table(comsol_context_tmp, last_temp, crate=None):
    file = open(os.path.join(comsol_context_tmp, "Input_T.txt"), "w")

    if crate is None:
        file.write("0 \t" + last_temp)
    else:
        # TODO: Get the cooling unit id and crop id from the crate and use that to
        # get newly added sl_buffer column from coolingunitcrop table, still 0.5 as
        # backup.
        # TODO: get the produce_id from the crate_id and calculate at produce level

        six_hours_ago = datetime.now().astimezone() - timedelta(hours=6)
        temp = crate is not None and (
            CoolingUnitSpecifications.objects.filter(
                cooling_unit=crate.cooling_unit, specification_type="TEMPERATURE"
            )
            .exclude(datetime_stamp__lte=six_hours_ago)
            .order_by("datetime_stamp")
        ) or ()

        # todo: from temp above, get all the set point values over the last 6 hours
        # and average them - expected: 6 values for ubibot, 24 values for ecozen.
        # idea: create an array of all set_point_values and then average them after
        # confirming there's no nulls (alternatively, null might not be an issue
        # for the average method)
        """
        # Given array with a null value (confirm what DB returns for null value
        num_array = [10, 50, 60, 50, None, 50]

        # Filter out None values and calculate average
        # Using a list comprehension to filter out None values
        filtered_array = [num for num in num_array if num is not None]

        # Calculate the average
        average = sum(filtered_array) / len(filtered_array) if filtered_array else None

        print("Original Array:", num_array)
        print("Filtered Array:", filtered_array)
        print("Average:", average)
        """

        i = 0
        try:
            if len(temp) == 0:
                file.write("0 \t" + last_temp)
            else:
                for t in temp:
                    seconds = (t.datetime_stamp - six_hours_ago).total_seconds()
                    seconds_rounded = 0 if i == 0 else math.floor(float(seconds))
                    file.write(str(seconds_rounded) + "\t" + str(t.value) + "\n")
                    i = +1
        except:
            file.write("0 \t")

    file.close()


# TODO: This function doesn't appear to be used and can be removed
def compute_dt_produce(produce_id, crate_id):
    # get current crate, cooling unit, cooling unit specification for latest temperature
    produce = Produce.objects.get(id=produce_id)
    crate = Crate.objects.get(id=crate_id)

    # if there is no temperature recorded, we cannot do a check-in. (we enforce temperature addition but we can never know)
    if not CoolingUnitSpecifications.objects.filter(
        cooling_unit=crate.cooling_unit, specification_type="TEMPERATURE"
    ):
        return None

    # create temporary directory (so we don't overwrite Input and Output Files)
    comsol_context_tmp = get_comsol_context_temp_dir()

    identifier = crate.produce.crop.digital_twin_identifier

    # assigns Set_T to the last_temp and T_set parameter if cooling unit has an Ecozen Sensor, otherwise set the last manual temperature in the cold room
    last_temp = float ( get_set_t( crate_id ) )


    # create contextual files
    comsol_write_initial_values(
        comsol_context_tmp,
        crate,
        quality_dt=produce.harvest_date / 100,
        temperature_dt=290,
        shelf_life_buffer=0.5,
        fruit_index=identifier,
        last_temp=last_temp,
    )

    # Don't pass on the crate so the historical data only includes the last_temp
    comsol_write_input_table(comsol_context_tmp, last_temp)

    try:
        comsol_compute(comsol_context_tmp, identifier)
    except subprocess.CalledProcessError:
        print("DT failed to run")

    print(
        f"finished DT run - crate {crate_id},identifier {identifier}, DT Contextual Path - {comsol_context_tmp}"
    )

    return comsol_context_tmp

def compute_dt_crate(crate_id):
    # get previous values from produce
    crate = Crate.objects.get(id=crate_id)

    # create temperature file from the last six hours
    if not CoolingUnitSpecifications.objects.filter(
        cooling_unit=crate.cooling_unit, specification_type="TEMPERATURE"
    ):
        return None

    # create temporary directory (so we don't overwrite Input and Output Files)
    comsol_context_tmp = get_comsol_context_temp_dir()

    identifier = crate.produce.crop.digital_twin_identifier

    # assigns Set_T to the last_temp and T_set parameter if cooling unit has an Ecozen Sensor, otherwise set the last manual temperature in the cold room
    last_temp = get_set_t( crate_id )

    # create contextual files
    comsol_write_input_table(comsol_context_tmp, last_temp, crate)
    comsol_write_initial_values(
        comsol_context_tmp,
        crate,
        quality_dt=crate.quality_dt,
        temperature_dt=crate.temperature_dt,
        shelf_life_buffer=0.5,
        fruit_index=identifier,
        last_temp=last_temp,
    )

    try:
        comsol_compute(comsol_context_tmp, identifier)
    except subprocess.CalledProcessError:
        print("DT failed to run")

    print(
        f"finished DT run - crate {crate_id},identifier {identifier}, DT Contextual Path - {comsol_context_tmp}"
    )

    return comsol_context_tmp


def comsol_get_output_data(comsol_context_tmp):
    output_pl_path = os.path.join(comsol_context_tmp, "output_PL.txt")
    output_values_path = os.path.join(comsol_context_tmp, "outputvalues.txt")

    timeout = time.time() + 30 # 30 seconds of timeout in the while loop

    # Hold while the file doesn't exist
    while not os.path.exists(output_pl_path) and not os.path.exists(output_values_path):
        time.sleep(1)
        if time.time() > timeout:
            raise TimeoutError(f"Looking for the output data in the dir {comsol_context_tmp} has timed out")

    # output pl - the file only has one row, we read it and split it. We take the last value and type it into an int
    pl = open(output_pl_path, "r")
    pl_lines = pl.readlines()

    ttp = int(float(pl_lines[0].split(" ")[-1][:-1]))


    # output values - get initial values from OutputValues and store for recomputation (will be initialInput in recomputing)
    ###
    values = open(output_values_path, "r")
    values_lines = values.readlines()
    # the file only has one row, we read it and split it. We take the last value and type it into an int
    new_values = list(filter(None, values_lines[0].split(" ")))
    new_values[-1].replace("\n", "")

    temperature_dt = new_values[2][:-1]
    quality_dt = new_values[1]

    return ttp, quality_dt, temperature_dt



def comsol_parse_output_produce(produce_id, comsol_context_tmp):
    print(f"parse output state: produce_id {produce_id}, comsol_context_tmp {comsol_context_tmp}")

    try:
        ttp, quality_dt, temperature_dt = comsol_get_output_data(comsol_context_tmp)

        crates = Crate.objects.filter(produce_id=produce_id)
        for crate in crates:
            Crate.objects.filter(id=crate.id).update(
                temperature_dt=temperature_dt,
                quality_dt=quality_dt,
                remaining_shelf_life=ttp,
                modified_dt=timezone.now(),
            )

    finally:
        # delete directory - when we have paths
        try:
            shutil.rmtree(comsol_context_tmp)
        except:
            pass


def comsol_parse_output_crate(crate_id, comsol_context_tmp):
    print(f"parse output state: crate_id {crate_id}, comsol_context_tmp {comsol_context_tmp}")

    try:
        ttp, quality_dt, temperature_dt = comsol_get_output_data(comsol_context_tmp)

        print(f"debug: ttp {ttp}, quality_dt {quality_dt}, temperature_dt {temperature_dt}")

        # store values alongside to all crates in the same produce that are not checked out

        Crate.objects.filter(
            # crates that have the same produce as the one we are parsing
            produce__crates__id=crate_id,
            # that are not checked out
            weight__gt=0
        ).update(
            temperature_dt=temperature_dt,
            quality_dt=quality_dt,
            remaining_shelf_life=ttp,
            modified_dt=timezone.now(),
        )

    finally:
        # delete directory - when we have paths
        try:
            shutil.rmtree(comsol_context_tmp)
        except:
            pass
