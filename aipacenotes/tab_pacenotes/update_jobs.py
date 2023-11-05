import time

from .rally_file import Pacenote
from aipacenotes import client as aip_client

def pacenote_job_id(pacenote):
    return pacenote.name()

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
        print(f"UpdateJob.run '{self.pacenote}'")

        # self._updated_at = time.time()
        self.update_ago_cache()

        voice = self.pacenote.voice()
        voice_config = self.store.settings_manager.voice_config(voice)

        if voice_config:
            # notebook = self.pacenote.notebook
            response = aip_client.post_create_pacenotes_audio(
                self.pacenote.note(),
                voice_config,
            )

            if response.status_code == 200:
                self.pacenote.write_file(response.content)
                self._status = UPDATE_JOB_STATUS_SUCCESS
            else:
                self._status = f'{UPDATE_JOB_STATUS_ERROR} {response.status_code}'
        else:
            self._status = f'{UPDATE_JOB_STATUS_ERROR} unknown voice: "{voice}"'

        self._updated_at = time.time()
        self.update_ago_cache()

        self.store.sort()
        self.store.prune()
        self.store.clear_lock(self.pacenote)
        done_signal.emit(self)

class UpdateJobsStore:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.jobs = []
        self.pacenote_ids_lock = {}

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
        two_minutes_ago = time.time() - 60*2

        def should_prune(job):
            is_success = job.status() == UPDATE_JOB_STATUS_SUCCESS
            is_old = job.updated_at() < two_minutes_ago
            return (is_success and is_old)
        
        new_jobs = []

        for job in self.jobs:
            if should_prune(job):
                self.clear_lock(job.pacenote)
            else:
                new_jobs.append(job)

        # self.jobs[:] = [job for job in self.jobs if not should_prune(job)]
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

        return job
    
    def clear_lock(self, pacenote):
        id = pacenote_job_id(pacenote)
        self.pacenote_ids_lock.pop(id, None)
    
    def has_job_for_pacenote(self, pacenote):
        id = pacenote_job_id(pacenote)
        if id in self.pacenote_ids_lock:
            job = self.pacenote_ids_lock[id]
            if job is not None:
                return True
            else:
                return False
        else:
            return False