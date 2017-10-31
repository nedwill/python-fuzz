"""
The main fuzzer code.
"""

import hashlib
import logging
import random
import string
import time
# from byte_feedback import ByteFeedback, ByteIOFeedback
from collections import defaultdict
from pathlib import Path

import coverage
from target import plist_target


class ShouldTrace:
    trace = True

    def __init__(self, filename):
        self.source_filename = filename


# CTracer ?
class Tracer(coverage.PyTracer):
    """Handles getting coverage."""

    def __init__(self):
        super().__init__()
        self.trace_arcs = True

        # TODO: see how coverage.py does this
        def should_trace(filename, frame):
            res = ShouldTrace(filename)
            if filename == 'fuzzer.py':
                res.trace = False
            return res

        self.data = {}
        self.trace = None
        self.should_trace = should_trace
        self.should_trace_cache = {}

    @property
    def edges(self):
        return self.data


class Fuzzer:
    """
    The main fuzzer object.
    """

    def __init__(self, target, corpus_dir):
        # io.BytesIO = ByteIOFeedback
        self.target = target
        self.corpus = []
        self.corpus_dir = corpus_dir
        # filename -> edges
        self.edges = defaultdict(set)
        to_import = list(corpus_dir.iterdir())
        for path in to_import:
            try:
                self.import_testcase(path)
            except Exception as exc:
                print("{} crashes `{}`, please fix.".format(path,
                                                            path.read_bytes()))
                raise exc
        if not to_import:
            self.test_one_input(b'A' * 64)
        if not self.edges:
            logging.error("No coverage found! "
                          "Does your target function do something?")
            exit()

    def import_testcase(self, path):
        testcase = path.read_bytes()
        self.test_one_input(testcase)

    @property
    def smallest_input(self):
        assert self.corpus
        return min(len(e) for e in self.corpus)

    def get_edges_from_input(self, data):
        tracer = Tracer()
        tracer.start()
        crashed = None
        try:
            self.target(data)
        except Exception as exc:
            # TODO: when shrinking check exception matches?
            crashed = exc
            self.write_crash_to_disk(data)
            raise exc
        tracer.stop()
        return tracer.edges, crashed

    def test_one_input(self, data):
        tracer_edges, _ = self.get_edges_from_input(data)
        has_new = False
        for name, edges in tracer_edges.items():
            if edges is None:
                continue
            edges = set(edges)
            if edges - self.edges[name]:
                has_new = True
            self.edges[name] |= edges
        if has_new:
            # if self.corpus:
            # print(len(data), min(len(e) for e in self.corpus))
            self.corpus.append(data)
            self.write_to_disk(bytes(data))
        return has_new
        # print(cov_data.measured_files())

        # def mutate_shuffle(data):
        #     pass

    def write_to_disk(self, data):
        name = hashlib.sha1(data).hexdigest()
        dest = self.corpus_dir.joinpath(name)
        if not dest.exists():
            dest.write_bytes(data)

    def write_crash_to_disk(self, data):
        name = 'crash-' + hashlib.sha1(data).hexdigest()
        dest = self.corpus_dir.joinpath(name)
        if not dest.exists():
            print("Writing crash to {}...".format(dest))
            dest.write_bytes(data)

    def mutate_erase_bytes(self, data):
        idx = random.randrange(len(data))
        return data[idx:random.randrange(idx, len(data))]

    def mutate_insert_bytes(self, data):
        idx = random.randrange(len(data))
        new_bytes = self.get_random_bytes(random.randrange(1, 5))
        return data[:idx] + new_bytes + data[idx:]

    def mutate_insert_repeated_bytes(self, data):
        idx = random.randrange(len(data))
        new_byte = self.get_random_byte()
        sz = random.randrange(16)
        data[idx:idx + sz] = bytearray(new_byte) * sz
        return data

    @staticmethod
    def get_random_bytes(size):
        # Use random here so we can fix the seed for tests.
        return bytearray(random.getrandbits(8) for _ in range(size))

    @staticmethod
    def get_random_byte():
        return random.getrandbits(8)

    def mutate_change_byte(self, data):
        idx = random.randrange(len(data))
        data[idx] = self.get_random_byte()
        return data

    def mutate_change_bit(self, data):
        idx = random.randrange(len(data))
        data[idx] ^= 1 << random.randrange(8)
        return data

    # def mutate_copy_part(self, data):
    #     pass

    # manual dict
    # auto dict
    # torc

    def mutate_change_ascii_integer(self, data):
        start = random.randrange(len(data))
        while start < len(data) and chr(data[start]) not in string.digits:
            start += 1
        if start == len(data):
            return data

        end = start
        while end < len(data) and chr(data[end]) in string.digits:
            end += 1

        value = int(data[start:end])
        choice = random.randrange(5)
        if choice == 0:
            value += 1
        elif choice == 1:
            value -= 1
        elif choice == 2:
            value //= 2
        elif choice == 3:
            value *= 2
        elif choice == 4:
            value *= value
            value = max(1, value)
            value = random.randrange(value)
        else:
            assert False

        to_insert = bytes(str(value), encoding='ascii')
        data[start:end] = to_insert
        return data

    # def mutate_change_binary_integer(self, data):
    #     pass

    # def crossover(self, data):
    #     pass

    def generate_input(self):
        assert self.corpus
        data = bytearray(random.choice(self.corpus))
        num_mutations = random.randrange(1, 5)
        for _ in range(num_mutations):
            if not data:
                return bytes()
            choice = random.randrange(6)
            if choice == 0:
                data = self.mutate_erase_bytes(data)
            elif choice == 1:
                data = self.mutate_insert_bytes(data)
            elif choice == 2:
                data = self.mutate_change_byte(data)
            elif choice == 3:
                data = self.mutate_change_bit(data)
            elif choice == 4:
                data = self.mutate_change_ascii_integer(data)
            elif choice == 5:
                data = self.mutate_insert_repeated_bytes(data)
            # elif choice == 5:
            #     data = self.mutate_copy_part(data)
            # elif choice == 5:
            #     data = self.mutate_change_binary_integer(data)
            else:
                assert False
        return bytes(data)  # ByteFeedback(data)

    def print_status(self, info, num_execs, start):
        elapsed = max(int(time.time() - start), 1)
        exec_s = num_execs // elapsed
        cov = sum(len(edges) for edges in self.edges.values())
        print("#{} {} cov: {} corpus: {} exec/s: {}".format(
            num_execs, info, cov, len(self.corpus), exec_s))

    def print_pulse(self, num_execs, start):
        self.print_status("pulse", num_execs, start)

    def print_new(self, num_execs, start):
        self.print_status("NEW", num_execs, start)

    def fuzz(self):
        num_execs = 0
        start = time.time()
        while True:
            data = self.generate_input()
            has_new = self.test_one_input(data)
            if has_new:
                self.print_new(num_execs, start)
            elif bin(num_execs).count("1") == 1:
                self.print_pulse(num_execs, start)
            num_execs += 1

    def minimize(self, data):
        # TODO: minimize using a few simple strategies
        edges, crashed = self.get_edges_from_input(data)
        # TODO: if it crashed, minimize while maintaining same
        # exception type. otherwise, maintain edge coverage
        # TODO: pipe tests through here before writing to disk


if __name__ == '__main__':
    fuzzer = Fuzzer(plist_target, Path('./corpus'))
    fuzzer.fuzz()
    # fuzzer.minimize(Path('corpus/crash-a51a56f8dc7dffdd8ff6b5c21bf5cfe8c6134724'))
