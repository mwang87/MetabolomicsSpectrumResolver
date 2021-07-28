import logging
import random

import locust

from usi_test_data import usis_to_test


random.seed(42)


@locust.events.quitting.add_listener
def _(environment, **kw):
    max_failure_rate = 0.01
    max_avg_response_time = 20000
    max_percentile_time = 0.95, 20000
    if environment.stats.total.fail_ratio > max_failure_rate:
        logging.error(f'Test failed due to failure ratio > '
                      f'{max_failure_rate:.0%}: '
                      f'{environment.stats.total.fail_ratio:.0%}')
        environment.process_exit_code = 1
    elif environment.stats.total.avg_response_time > max_avg_response_time:
        logging.error('Test failed due to average response time ratio > %d ms:'
                      ' %d ms', max_avg_response_time,
                      environment.stats.total.avg_response_time)
        environment.process_exit_code = 1
    elif environment.stats.total.get_response_time_percentile(
            max_percentile_time[0]) > max_percentile_time[1]:
        logging.error('Test failed due to %dth percentile response time > %d '
                      'ms', max_percentile_time[0], max_percentile_time[1])
        environment.process_exit_code = 1
    else:
        environment.process_exit_code = 0


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
        self.client.get(f'/png/?usi1={usi}', name='/png/')

    @locust.task
    def generate_svg(self):
        usi = random.choice(usis_to_test)
        self.client.get(f'/svg/?usi1={usi}', name='/svg/')

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

    @locust.task
    def generate_mirror_json(self):
        usi1 = random.choice(usis_to_test)
        usi2 = random.choice(usis_to_test)
        self.client.get(f'/json/mirror/?usi1={usi1}&usi2={usi2}',
                        name='/json/mirror/')
