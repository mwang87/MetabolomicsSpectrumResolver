import random

import locust

from usi_test_data import usis_to_test


random.seed(42)


class UsiLoadTester(locust.HttpUser):
    wait_time = locust.between(1, 10)

    # Default host if not otherwise specified.
    host = 'https://metabolomics-usi.ucsd.edu/'

    @locust.task(3)
    def render_spectrum(self):
        usi = random.choice(usis_to_test)
        self.client.get(f'/spectrum/?usi={usi}', name='/spectrum/')

    @locust.task
    def generate_png(self):
        usi = random.choice(usis_to_test)
        self.client.get(f'/png/?usi={usi}', name='/png/')

    @locust.task
    def generate_svg(self):
        usi = random.choice(usis_to_test)
        self.client.get(f'/svg/?usi={usi}', name='/svg/')

    @locust.task(3)
    def render_mirror_spectrum(self):
        usi1 = random.choice(usis_to_test)
        usi2 = random.choice(usis_to_test)
        self.client.get(f'/mirror/?usi1={usi1}&usi2={usi2}', name='/mirror/')

    @locust.task
    def generate_mirror_png(self):
        usi1 = random.choice(usis_to_test)
        usi2 = random.choice(usis_to_test)
        self.client.get(f'/png/mirror/?usi1={usi1}&usi2={usi2}',
                        name='/png/mirror/')

    @locust.task
    def generate_mirror_svg(self):
        usi1 = random.choice(usis_to_test)
        usi2 = random.choice(usis_to_test)
        self.client.get(f'/svg/mirror/?usi1={usi1}&usi2={usi2}',
                        name='/svg/mirror/')
