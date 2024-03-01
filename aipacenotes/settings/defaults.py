default_settings = {
    'beam_user_home':   '$HOME/AppData/Local/BeamNG.drive/latest',
    'mods_dir':     '$beam_user_home/mods',
    'unpacked_mod_dir': '$beam_user_home/mods/unpacked/beamng-aipacenotes-mod',
    'notebooks_search_paths': [
        '$beam_user_home/gameplay/missions',
        '$unpacked_mod_dir/gameplay/missions',
    ],
    'settings_dir':       '$beam_user_home/settings/aipacenotes',
    'settings_fname_user': '$settings_dir/settings.json',
    'temp_dir':           '$beam_user_home/temp/aipacenotes',
    'transcripts_fname':   '$settings_dir/desktop.transcripts.json',
    'static_pacenotes_fnames': [
        '$mods_dir/repo/aipacenotes.zip/settings/aipacenotes/static_pacenotes.json',
        '$mods_dir/aipacenotes.zip/settings/aipacenotes/static_pacenotes.json',
        '$unpacked_mod_dir/settings/aipacenotes/static_pacenotes.json',
        '$settings_dir/static_pacenotes.json'
    ],
    'recording_cut_delay': 0.3,
    'voice_files': [
        # lowest priority.
        # voices from zipped mod in repo.
        '$mods_dir/repo/aipacenotes.zip/settings/aipacenotes/default.voices.json',
        # voices from zipped mod at mods root.
        '$mods_dir/aipacenotes.zip/settings/aipacenotes/default.voices.json',
        # voices from unzipped mod during development.
        '$unpacked_mod_dir/settings/aipacenotes/default.voices.json',
        '$beam_user_home/mods/unpacked/aipacenotes',
        # voices from user settings.
        # highest priority.
        '$settings_dir/user.voices.json',
    ]
}
