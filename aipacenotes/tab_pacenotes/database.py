from . import (
    Pacenote,
)

class Database():
    def __init__(self):
        self.pacenotes = []
        # unique index pacenotes on id
        self.unique_index_pn_id = {}
    
    def select(self, pnid):
        if pnid in self.unique_index_pn_id:
            return self.unique_index_pn_id[pnid]
        else:
            return None
    
    def select_with_fname(self, query_pacenotes_fname):
        result = []

        for pn in self.pacenotes:
            if pn.pacenotes_fname == query_pacenotes_fname:
                result.append(pn)

        return result
    
    def delete(self, pnid):
        pn = self.select(pnid)
        self.pacenotes.remove(pn)
        del self.unique_index_pn_id[pnid]
    
    def insert(self, pacenote):
        pnid = pacenote.id
        if pnid in self.unique_index_pn_id:
            raise ValueError(f'insert: pacenote exists with id={pnid}')
        self.pacenotes.append(pacenote)
        self.unique_index_pn_id[pnid] = pacenote
        pacenote.touch()
        return pacenote
    
    def upsert(self, pacenote):
        pnid = pacenote.id
        if pnid in self.unique_index_pn_id:
            return self.update(pacenote)
        else:
            return self.insert(pacenote)
    
    def update(self, pacenote):
        pnid = pacenote.id
        existing = self.unique_index_pn_id[pnid]
        if existing is None:
            raise ValueError(f'update: pacenote doesnt exist with id={pnid}')

        def update_attrs(attrs):
            update_made = False
            for attr in attrs:
                old_val = getattr(existing, attr)
                new_val = getattr(pacenote, attr)
                if new_val != old_val:
                    setattr(existing, attr, new_val)
                    print(f"updated field {attr} from '{old_val}' to '{new_val}'")
                    update_made = True
            return update_made

        if update_attrs(Pacenote.static_attrs):
            existing.touch()
            existing.set_dirty()

        return existing