import os
from subprocess import Popen
from autode.log import logger
from autode.exceptions import XYZsNotFound


class Calculation:

    def get_energy(self):
        logger.info('Getting energy from {}'.format(self.output_filename))
        if self.terminated_normally:
            return self.method.get_energy(self)

        logger.error(
            'Calculation did not terminate normally – not returning the energy')
        return None

    def optimisation_converged(self):
        logger.info('Checking to see if the geometry converged')
        return self.method.optimisation_converged(self)

    def optimisation_nearly_converged(self):
        """
        Check whether a calculation has nearly converged and may just need more geometry optimisation steps to
        complete successfully
        :return: (bool)
        """
        return self.method.optimisation_nearly_converged(self)

    def get_imag_freqs(self):
        logger.info('Finding imaginary frequencies in cm-1')
        return self.method.get_imag_freqs(self)

    def get_normal_mode_displacements(self, mode_number):
        """
        Get the displacements along a mode for each of the n_atoms in the structure will return a list of length
        n_atoms each with 3 components (x, y, z)

        :param mode_number: (int) normal mode number. 6 will be the first vibrational mode (indexed from 0 in ORCA)
        :return:
        """
        return self.method.get_normal_mode_displacements(self, mode_number)

    def get_final_xyzs(self):
        logger.info('Getting final xyzs from {}'.format(self.output_filename))
        xyzs = self.method.get_final_xyzs(self)

        if len(xyzs) == 0:
            logger.error(
                'Could not get xyzs from calculation file {}'.format(self.name))
            raise XYZsNotFound

        return xyzs

    def get_scan_values_xyzs_energies(self):
        return self.method.get_scan_values_xyzs_energies(self)

    def calculation_terminated_normally(self):
        logger.info('Checking to see if {} terminated normally'.format(
            self.output_filename))
        return self.method.calculation_terminated_normally(self)

    def set_output_file_lines(self):
        self.output_file_lines = [line for line in open(
            self.output_filename, 'r', encoding="utf-8")]
        self.rev_output_file_lines = list(reversed(self.output_file_lines))
        return None

    def generate_input(self):
        logger.info('Generating input file for {}'.format(self.name))
        return self.method.generate_input(self)

    def execute_calculation(self):
        logger.info('Running calculation {}'.format(self.input_filename))

        if self.input_filename is None:
            logger.error(
                'Could not run the calculation. Input filename not defined')
            return

        if self.method.available is False:
            logger.critical('Electronic structure method is not available')
            exit()

        if not os.path.exists(self.input_filename):
            logger.error(
                'Could not run the calculation. Input file does not exist')
            return

        if os.path.exists(self.output_filename):
            self.output_file_exists = True
            self.set_output_file_lines()

        if self.output_file_exists:
            if self.calculation_terminated_normally():
                logger.info(
                    'Calculated already terminated successfully. Skipping')
                return self.set_output_file_lines()

        logger.info(
            'Setting the number of OMP threads to {}'.format(self.n_cores))
        os.environ['OMP_NUM_THREADS'] = str(self.n_cores)

        with open(self.output_filename, 'w') as output_file:

            params = [self.method.path, self.input_filename]
            if self.flags is not None:
                params += self.flags

            subprocess = Popen(params, stdout=output_file,
                               stderr=open(os.devnull, 'w'))
        subprocess.wait()
        logger.info('Calculation {} done'.format(self.output_filename))

        return self.set_output_file_lines()

    def run(self):
        logger.info('Running calculation of {}'.format(self.name))

        self.generate_input()
        self.execute_calculation()
        self.terminated_normally = self.calculation_terminated_normally()

        return None

    def __init__(self, name, molecule, method, keywords=None, n_cores=1, max_core_mb=1000, bond_ids_to_add=None,
                 optts_block=None, opt=False, distance_constraints=None):
        """
        :param name: (str)
        :param molecule: (object) a Molecule object
        :param n_cores: (int)
        :param bond_ids_to_add: (list(tuples))
        :param optts_block: (bool)
        :param distance_constraints: (dict) keys: tuple of atom ids (indexed from 0), values: float of the distance
        """

        self.name = name
        self.xyzs = molecule.xyzs
        self.charge = molecule.charge
        self.mult = molecule.mult
        self.method = method
        self.keywords = keywords
        self.flags = None
        self.opt = opt

        self.solvent = molecule.solvent

        self.n_cores = n_cores
        # Maximum memory per core to use
        self.max_core_mb = max_core_mb

        self.bond_ids_to_add = bond_ids_to_add
        self.optts_block = optts_block
        self.distance_constraints = distance_constraints

        self.input_filename = None
        self.output_filename = None

        self.output_file_exists = False
        self.terminated_normally = False
        self.output_file_lines = None
        self.rev_output_file_lines = None

        if molecule.solvent is not None:
            if molecule.solvent.lower() not in method.aval_solvents:                    # Lowercase everything
                logger.critical(
                    'Solvent is not available. Cannot run the calculation')
                print('Available solvents are {}'.format(method.aval_solvents))
                exit()

        if self.xyzs is None:
            logger.error('Have no xyzs. Can\'t make a calculation')
            return

        self.n_atoms = len(self.xyzs)