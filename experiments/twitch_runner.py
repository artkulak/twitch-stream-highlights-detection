# Twitch API

import twitch

helix = twitch.Helix('5svdpyta9de8v3ddeafwdcam2shi8z', '66tk3ib98g6uxenlzrcwqkudvx6tsk')

for user, videos in helix.users(['rogue']).videos(first=1):
    for video in videos:
        print(video)