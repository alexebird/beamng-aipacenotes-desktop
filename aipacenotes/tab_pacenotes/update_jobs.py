import logging
import time

from aipacenotes import client as aip_client

def pacenote_job_id(pacenote):
    mission_id = pacenote.notebook.notebook_file.mission_id()
    return f'{mission_id}_{pacenote.notebook.name()}_{pacenote.codriver_name()}_{pacenote.name()}'

UPDATE_JOB_STATUS_UPDATING = 'updating'
UPDATE_JOB_STATUS_SUCCESS = 'success'
UPDATE_JOB_STATUS_ERROR = 'error'

class UpdateJob:
    def __init__(self, store, pacenote):
        self.store = store
        self.pacenote = pacenote
        self._status = UPDATE_JOB_STATUS_UPDATING
        self._created_at = time.time()
        self._updated_at = self._created_at
        self._cached_updated_at_str = "0s ago"

    def update_ago_cache(self):
        seconds = time.time() - self._updated_at
        if seconds < 60:
            self._cached_updated_at_str = f"{int(seconds)}s ago"
        else:
            self._cached_updated_at_str = f"{round(seconds / 60.0)}m ago"

    def created_at(self):
        return self._created_at

    def updated_at(self):
        return self._updated_at

    def status(self):
        return self._status

    def run(self, done_signal):
        logging.debug(f"UpdateJob.run '{self.pacenote}'")

        # self._updated_at = time.time()
        self.update_ago_cache()

        voice = self.pacenote.voice()
        vc_settings = self.store.settings_manager.voice_config(voice)
        vc_mission = self.pacenote.notebook.notebook_file.mission_voice_config(voice)

        voice_config = vc_settings
        # if there is a mission voice file, prioritize that over the settings files.
        if vc_mission:
            voice_config = vc_mission

        if voice_config:
            response = aip_client.post_create_pacenotes_audio(
                self.pacenote.note(),
                voice_config,
            )

            if response.status_code == 200:
                self.pacenote.write_file(response.content)
                self._status = UPDATE_JOB_STATUS_SUCCESS
            else:
                logging.error(f"network error")
                self._status = UPDATE_JOB_STATUS_ERROR
                self.store.set_error(self)
        else:
            logging.error(f"no voice_config")
            self._status = UPDATE_JOB_STATUS_ERROR
            self.store.set_error(self)

        self._updated_at = time.time()
        self.update_ago_cache()

        self.store.sort()
        self.store.prune()
        self.store.clear_lock(self)
        done_signal.emit(self)

class UpdateJobsStore:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.jobs = []
        self.pacenote_ids_lock = {}
        self.pacenote_ids_error = {}

    def __len__(self):
        return len(self.jobs)

    def update_job_time_agos(self):
        for job in self.jobs:
            job.update_ago_cache()

    def sort(self):
        status_order = {
            UPDATE_JOB_STATUS_ERROR: 0,
            UPDATE_JOB_STATUS_UPDATING: 1,
            UPDATE_JOB_STATUS_SUCCESS: 2,
        }

        self.jobs.sort(
            key=lambda job: (status_order[job.status()], -job.updated_at())
        )

    def prune(self):
        prune_threshold_sec = time.time() - 30

        def should_prune(job):
            is_success = job.status() == UPDATE_JOB_STATUS_SUCCESS
            is_error = job.status() == UPDATE_JOB_STATUS_ERROR
            is_old = job.updated_at() < prune_threshold_sec
            return ((is_error or is_success) and is_old)

        new_jobs = []

        for job in self.jobs:
            if should_prune(job):
                self.clear_lock(job)
                self.clear_error(job)
            else:
                new_jobs.append(job)

        self.jobs = new_jobs

    def get(self, idx):
        return self.jobs[idx]

    def add_job(self, pacenote):
        id = pacenote_job_id(pacenote)

        if self.has_job_for_pacenote(pacenote):
            return None

        job = UpdateJob(self, pacenote)

        self.jobs.append(job)
        self.pacenote_ids_lock[id] = job
        self.sort()

        return job

    def set_error(self, job):
        pacenote = job.pacenote
        id = pacenote_job_id(pacenote)
        self.pacenote_ids_error[id] = job

    def clear_lock(self, job):
        pacenote = job.pacenote
        id = pacenote_job_id(pacenote)
        # if id in self.pacenote_ids_lock:
            # self.pacenote_ids_error[id] = self.pacenote_ids_lock[id]
        self.pacenote_ids_lock.pop(id, None)

    def clear_error(self, job):
        pacenote = job.pacenote
        id = pacenote_job_id(pacenote)
        self.pacenote_ids_error.pop(id, None)

    def has_job_for_pacenote(self, pacenote):
        id = pacenote_job_id(pacenote)

        rv = False

        if id in self.pacenote_ids_lock:
            job = self.pacenote_ids_lock[id]
            if job is not None:
                # return True
                rv = True
            # else:
                # return False

        logging.debug(f"UpdateJobsStore.has_job_for_pacenote {pacenote.short_name()} | lock rv={rv}")

        if id in self.pacenote_ids_error:
            job = self.pacenote_ids_error[id]
            if job is not None:
                # return True
                rv = True
            # else:
                # return False

        logging.debug(f"UpdateJobsStore.has_job_for_pacenote {pacenote.short_name()} | error rv={rv}")

        return rv

    def print(self):
        logging.debug("UpdateJobsStore")
        logging.debug("  pacenote_ids_lock")
        for id in self.pacenote_ids_lock:
            logging.debug(f"    - {id}")
        logging.debug("  pacenote_ids_error")
        for id in self.pacenote_ids_error:
            logging.debug(f"    - {id}")
        logging.debug("------------------------------------------------")
