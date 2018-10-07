from threading import Thread, Event, Lock
from time import time, sleep

TIME_STEP = 0.05


class Clock(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.elapsed_time: float = 0
        self.speed: float = 1
        self.running: Event = Event()
        self.running.set()
        self._stopped: bool = False
        self._dead: Event = Event()
        self.elapsed_time_lock = Lock()

    def run(self):
        prev_time: float = time()
        while not self._stopped:
            if not self.running.is_set():
                self.running.wait()
                prev_time = time()

            sleep(TIME_STEP)
            with self.elapsed_time_lock:
                current_time: float = time()
                self.elapsed_time += (current_time - prev_time) * self.speed
            prev_time = current_time
        self._dead.set()

    def pause(self):
        """Pause the clock"""
        self.running.clear()

    def resume(self):
        """Resume the clock"""
        self.running.set()

    def stop(self):
        """Stop the clock"""
        self.running.set()
        self._stopped = True
        self._dead.wait()

    def set_elapsed_time(self, elapsed_time: float):
        """Set the elapsed time of the clock"""
        with self.elapsed_time_lock:
            self.elapsed_time = elapsed_time


def main():
    timer = Clock()
    timer.start()
    print(timer.elapsed_time, 'Should be ~0')
    print('Alive? ', timer.is_alive())
    sleep(2)
    print(timer.elapsed_time, 'Should be ~2')
    timer.stop()


if __name__ == '__main__':
    main()
