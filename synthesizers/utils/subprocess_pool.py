from pickle import dumps, loads
import subprocess

def init_process(module_name):
    return subprocess.Popen(f'python -m {module_name}', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

class SubprocessPool:

    def __init__(self, n_workers, module_name):
        self.n_workers = n_workers
        self.module_name = module_name
        self.workers = [init_process(module_name) for _ in range(n_workers)]
        self.active_workers = []
        self.next_worker = 0

    def __del__(self):
        for worker in self.active_workers:
            worker.stdin.close()
            worker.stdout.close()

    def map(self, func, argss):
        resultss = []
        for args in argss:
            if len(self.active_workers) == self.n_workers:
                worker = self.active_workers.pop(0)
                header = bytearray()
                header.extend(worker.stdout.read(8))
                while header[-8:] != b'\x00\x00\x00\x00\x00\x00\x00\x00':
                    header.extend(worker.stdout.read(1))
                length = int.from_bytes(worker.stdout.read(8), byteorder='big')
                result = bytearray()
                print(f"MAP: got length {length}")
                while length > len(result):
                    to_read = min(length-len(result), 4096)
                    print(f"MAP: reading {to_read}")
                    result.extend(worker.stdout.read(to_read))
                print(f"MAP: read {len(result)} in total")
                resultss.append(loads(result))
            worker = self.workers[self.next_worker]
            self.next_worker = (self.next_worker + 1) % self.n_workers
            self.active_workers.append(worker)
            pickled = dumps((func, args))
            worker.stdin.write(b'\x00\x00\x00\x00\x00\x00\x00\x00')
            worker.stdin.write(len(pickled).to_bytes(8, byteorder='big'))
            while(len(pickled) > 0):
                written = worker.stdin.write(pickled[:4096])
                pickled = pickled[written:]
            worker.stdin.flush()
        while self.active_workers:
            worker = self.active_workers.pop(0)
            header = bytearray()
            header.extend(worker.stdout.read(8))
            while header[-8:] != b'\x00\x00\x00\x00\x00\x00\x00\x00':
                header.extend(worker.stdout.read(1))
            length = int.from_bytes(worker.stdout.read(8), byteorder='big')
            result = bytearray()
            print(f"MAP: got length {length}")
            while length > len(result):
                to_read = min(length-len(result), 4096)
                print(f"MAP: reading {to_read}")
                result.extend(worker.stdout.read(to_read))
            print(f"MAP: read {len(result)} in total")
            resultss.append(loads(result))
        return resultss