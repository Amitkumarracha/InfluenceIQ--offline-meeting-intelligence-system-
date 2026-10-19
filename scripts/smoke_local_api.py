"""Exercise real offline API processing in isolated local state, leaving user accounts intact."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ppt', type=Path, help='Optional local PPTX fixture')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    work=root/'.runtime/validation'/('api-readiness-'+secrets.token_hex(4))
    work.mkdir(parents=True, mode=0o700)
    os.environ.update(MAI_RUNTIME_DIR=str(work/'runtime'), MAI_DB_PATH=str(work/'test.db'),
                      MAI_DATA_DIR=str(work/'uploads'), MAI_ALLOW_REGISTRATION='1',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='4')
    from fastapi.testclient import TestClient
    from backend.api import app
    audio=work/'silence.wav'
    with wave.open(str(audio),'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000); output.writeframes(bytes(64000))
    attempts=[]
    original=socket.socket.connect
    def offline(*a,**k):
        attempts.append(True)
        raise AssertionError('API inference attempted a network connection')
    socket.socket.connect=offline
    try:
        with TestClient(app) as client:
            assert client.get('/api/health').json()['offline']
            credentials={'email':'readiness@example.invalid', 'password':secrets.token_urlsafe(20)}
            response=client.post('/api/auth/register',json=credentials); assert response.status_code==200, response.text
            auth={'Authorization':'Bearer '+response.json()['token']}
            with audio.open('rb') as stream:
                files=[('audio',('silence.wav',stream,'audio/wav'))]
                ppt=args.ppt.open('rb') if args.ppt else None
                try:
                    if ppt: files.append(('ppt',('validation.pptx',ppt,'application/vnd.openxmlformats-officedocument.presentationml.presentation')))
                    response=client.post('/api/analyze',headers=auth,files=files,
                        data={'title':'Readiness silence fixture','language':'auto','model_size':'small','diarization':'auto'})
                finally:
                    if ppt:ppt.close()
            assert response.status_code==202,response.text
            identifier=response.json()['meeting_id']
            for _ in range(120):
                meeting=client.get('/api/meetings/'+identifier,headers=auth).json()
                if meeting['status'] in {'completed','failed'}:break
                time.sleep(.5)
            assert meeting['status']=='completed',meeting.get('error')
            assert meeting['data']['transcript_segments']==[]
            assert not meeting['data']['processing']['speaker_separation']
            assert meeting['data']['participants']==[]
            for format in ('json','md','txt','srt','vtt','csv'):
                assert client.get('/api/meetings/'+identifier+'/export',headers=auth,params={'format':format}).status_code==200
            assert client.get('/api/meetings/'+identifier).status_code in (401,403)
            assert client.get('/').status_code==200
            assert not attempts
            result={'passed':True,'isolated_state':str(work.relative_to(root)),
                    'auth':True,'real_worker':True,'silence_abstention':True,'exports':6,
                    'frontend_served':True,'network_connections':len(attempts),
                    'scope':'Real local API workflow on digital silence, not recognition accuracy.'}
            (work/'result.json').write_text(json.dumps(result,indent=2))
            print(json.dumps(result,indent=2))
    finally:
        socket.socket.connect=original


if __name__=='__main__':main()
