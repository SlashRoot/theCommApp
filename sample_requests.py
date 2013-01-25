from what_apps.comm import comm_settings
import json

TYPICAL_TWILIO_REQUEST = {
    'AccountSid':     'AC260e405c96ce1eddffbddeee43a13004',
    'ToZip':     '12561',
    'FromState':     'NY',
    'Called':     '+18456338330',
    'FromCountry':     'US',
    'CallerCountry':     'US',
    'CalledZip':     '12561',
    'Direction':     'inbound',
    'FromCity':     'KINGSTON',
    'CalledCountry':     'US',
    'Duration':     '1',
    'CallerState':     'NY',
    'CallSid':     'CAbf093b318fdd9ac46ce92482c4ef55f4',
    'CalledState':     'NY',
    'From':     '+18454300941',
    'CallerZip':     '12484',
    'FromZip':     '12484',
    'CallStatus':     'in-progress',
    'ToCity':     'NEW PALTZ',
    'ToState':     'NY',
    'To':     '+18456338330',
    'CallDuration':     '19',
    'ToCountry':     'US',
    'CallerCity':     'KINGSTON',
    'ApiVersion':     '2010-04-01',
    'Caller':     '+18454300941',
    'CalledCity':     'NEW PALTZ',
                          }

TYPICAL_TWILIO_VOICEMAIL_REQUEST = {
                                    u'FromZip': [u'12553'], 
                                    u'From': [u'+18455975323'], 
                                    u'FromCity': [u'NEWBURGH'], 
                                    u'ApiVersion': [u'2010-04-01'], 
                                    u'To': [u'+14155992671'], 
                                    u'ToCity': [u'NOVATO'], 
                                    u'CalledState': [u'CA'], 
                                    u'FromState': [u'NY'], 
                                    u'Direction': [u'inbound'], 
                                    u'CallStatus': [u'in-progress'], 
                                    u'ToZip': [u'94949'], 
                                    u'CallerCity': [u'NEWBURGH'], 
                                    u'FromCountry': [u'US'], 
                                    u'CalledCity': [u'NOVATO'], 
                                    u'CalledCountry': [u'US'], 
                                    u'Caller': [u'+18455975323'], 
                                    u'CallerZip': [u'12553'], 
                                    u'AccountSid': [u'AC260e405c96ce1eddffbddeee43a13004'], 
                                    u'Called': [u'+14155992671'], 
                                    u'CallerCountry': [u'US'], 
                                    u'CalledZip': [u'94949'], 
                                    u'CallSid': [u'CAbf093b318fdd9ac46ce92482c4ef55f4'], 
                                    u'CallerState': [u'NY'], 
                                    u'ToCountry': [u'US'], 
                                    u'ToState': [u'CA']
                                    }

TYPICAL_TWILIO_VOICEMAIL_RECORDING = {
                                      u'FromZip': [u'12553'], 
                                      u'From': [u'+18455975323'], 
                                      u'FromCity': [u'NEWBURGH'], 
                                      u'ApiVersion': [u'2010-04-01'], 
                                      u'To': [u'+14155992671'], 
                                      u'RecordingUrl': [u'http://api.twilio.com/2010-04-01/Accounts/AC260e405c96ce1eddffbddeee43a13004/Recordings/REfb08671c82d09ea527ecd27a27aa114e'], #An actual mp3 file, but a test voicemail from Tim.  Safe to make public. 
                                      u'ToCity': [u'NOVATO'], 
                                      u'CalledState': [u'CA'], 
                                      u'FromState': [u'NY'], 
                                      u'Direction': [u'inbound'], 
                                      u'RecordingDuration': [u'13'], 
                                      u'CallStatus': [u'completed'], 
                                      u'ToZip': [u'94949'], 
                                      u'Digits': [u'hangup'], 
                                      u'CallerCity': [u'NEWBURGH'], 
                                      u'RecordingSid': [u'REfb08671c82d09ea527ecd27a27aa114e'], 
                                      u'FromCountry': [u'US'], 
                                      u'CalledCity': [u'NOVATO'], 
                                      u'CalledCountry': [u'US'], 
                                      u'Caller': [u'+18455975323'], 
                                      u'CallerZip': [u'12553'], 
                                      u'AccountSid': [u'AC260e405c96ce1eddffbddeee43a13004'], 
                                      u'Called': [u'+14155992671'], 
                                      u'CallerCountry': [u'US'], 
                                      u'CalledZip': [u'94949'], 
                                      u'CallSid': [u'CA1ed0859073bed8ee2d0f07f0a8f471cc'], 
                                      u'CallerState': [u'NY'], 
                                      u'ToCountry': [u'US'], 
                                      u'ToState': [u'CA']
                                      }

TYPICAL_TWILIO_PICKUP_BYPASS_REQUEST = {
'AccountSid':'AC260e405c96ce1eddffbddeee43a13004',
'AnsweredBy':'human',
'ApiVersion':'2010-04-01',
'CallSid':'CAf2510b2132c54d78b9aebc0a17d871f0',
'CallStatus':'in-progress',
'Called':'+18454300941',
'CalledCity':'KINGSTON',
'CalledCountry':'US',
'CalledState':'NY',
'CalledZip':'12484',
'Caller':'+18456338330',
'CallerCity':'NEW PALTZ',
'CallerCountry':'US',
'CallerState':'NY',
'CallerZip':'12561',
'Direction':'outbound-api',
'From':'+18456338330',
'FromCity':'NEW PALTZ',
'FromCountry':'US',
'FromState':'NY',
'FromZip':'12561',
'To':'+18454300941',
'ToCity':'KINGSTON',
'ToCountry':'US',
'ToState':'NY',
'ToZip':'12484',
}                                        


TYPICAL_TROPO_REQUEST = '{"session":{"id":"98f3a0633f854e4aad70abe26ce4e99f","accountId":"97442","timestamp":"2011-10-24T22:44:53.727Z","userType":"HUMAN","initialText":null,"callId":"e244f37c086e62cfe02cd4781cbe9778","to":{"id":"8452043574","name":"+18452043574","channel":"VOICE","network":"SIP"},"from":{"id":"8455550000","name":"+18455550000","channel":"VOICE","network":"SIP"},"headers":{"x-sbc-contact":"<sip:+18453808139@192.168.37.72:5060>","Content-Length":"434","x-sbc-remote-party-id":"<sip:+18453808139@192.168.37.72:5060>;privacy=off;screen=no","x-sbc-call-id":"134614484_1573873@192.168.37.72","x-sid":"26a07a6e76861ce397c05f37000407fa","CSeq":"1 INVITE","Via":"SIP/2.0/UDP 10.6.63.186:5060;rport=5060;branch=z9hG4bK-1bb174-6c2d2eaf-336be783-2aaac4c7bbb8","x-sbc-accept":"application/sdp","x-sbc-to":"<sip:+18452043574@67.231.8.93>","From":"<sip:8453808139@10.6.63.186:5060>;tag=2aaac53c0220-0-13c4-6009-1bb174-5bb85655-1bb174","x-sbc-from":"<sip:+18453808139@192.168.37.72;isup-oli=61>;tag=gK063c6859","x-sbc-allow":"BYE","x-voxeo-sbc-name":"10.6.63.186","x-accountid":"2","Contact":"<sip:8453808139@10.6.63.186:5060>","To":"<sip:8452043574@ppid410.romeo.orl.tropo.com>","x-voxeo-sbc":"true","User-Agent":"VCS11.5.55126.0","x-voxeo-to":"<sip:+18452043574@67.231.8.93>","x-appid":"24601","x-sbc-content-disposition":"session;handling=required","x-sbc-request-uri":"sip:+18452043574@sip.tropo.com","Max-Forwards":"70","x-sbc-max-forwards":"56","x-voxeo-sbc-session-id":"26a07a6e76861ce397c05f37000407fa","x-sbc-record-route":"<sip:67.231.8.195;lr=on;ftag=gK063c6859>,<sip:67.231.8.93;lr=on;ftag=gK063c6859>","Call-ID":"1319496293722-16845dc0-ac092ff0-0006bf78@10.6.63.186","Content-Type":"application/sdp"}}}'
TYPICAL_TROPO_REQUEST_AFTER_REST = '{"session":{"id":"3010a200d38c2e2ae99ac9e1dcd6ec39","accountId":"97442","timestamp":"2011-10-27T18:54:49.697Z","userType":"NONE","initialText":null,"callId":null,"parameters":{"token":"09db1e64c7db4045a459606daae7794c158f859b2e321ab908eda9bb2c362ff3555c69d496c5aa48008f6543","action":"create"}}}'
TYPICAL_TROPO_PICKUP_ALERT = '{"result":{"sessionId":"f1176436f4fe1de30fef3c19d4a1995f","callId":"e244f37c086e62cfe02cd4781cbe9778","state":"ANSWERED","sessionDuration":3,"sequence":1,"complete":true,"error":null}}'
TYPICAL_TROPO_RESULT_REQUEST = '{"result":{"sessionId":"2b6428bf4f6ff8c66e0d95b5afa69b5d","callId":"701b7e9c67d225331dcf1e6333796ff1","state":"ANSWERED","sessionDuration":29,"sequence":2,"complete":true,"error":null,"actions":{"name":"response","attempts":2,"disposition":"SUCCESS","confidence":50,"interpretation":"' + str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']) + '","utterance":"' + str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']) + '","concept":"' + str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']) + '","value":"' + str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']) + '","xml":"<?xml version=\"1.0\"?>\r\n<result grammar=\"1@a6454f44.vxmlgrammar\">\r\n    <interpretation grammar=\"1@a6454f44.vxmlgrammar\" confidence=\"50\">\r\n        \r\n      <input mode=\"speech\">' + str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']) + '<\/input>\r\n    <\/interpretation>\r\n<\/result>\r\n"}}}'

#Tropo sends a JSON with XML 
TYPICAL_TROPO_RESULT_REQUEST_DICT = {u'result': {u'sessionDuration': 29, u'complete': True, u'sequence': 2, u'callId': u'701b7e9c67d225331dcf1e6333796ff1', u'state': u'ANSWERED', u'actions': {u'xml': u'<?xml version="1.0"?>\r\n<result grammar="1@a6454f44.vxmlgrammar">\r\n    <interpretation grammar="1@a6454f44.vxmlgrammar" confidence="50">\r\n        \r\n      <input mode="speech">Pies and Sledgehammers</input>\r\n    </interpretation>\r\n</result>\r\n', u'confidence': 50, u'concept': str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']), u'interpretation': str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']), u'name': u'response', u'value': str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call']), u'attempts': 2, u'disposition': u'SUCCESS', u'utterance': str(comm_settings.SLASHROOT_EXPRESSIONS['phrase_to_answer_call'])}, u'sessionId': u'2b6428bf4f6ff8c66e0d95b5afa69b5d', u'error': None}} 
TYPICAL_TROPO_RESULT_REQUEST = json.dumps(TYPICAL_TROPO_RESULT_REQUEST_DICT) 

TYPICAL_TROPO_VOICEMAIL_REQUEST = '{"result":{"sessionId":"98f3a0633f854e4aad70abe26ce4e99f","callId":"d216db222e63fd0ff67363e19730cb36","state":"ANSWERED","sessionDuration":40,"sequence":1,"complete":true,"error":null}}'
SAMPLE_VOICEMAIL_WORDS = "Test test test voice to voice test recording troubles recording hello ..."
TYPICAL_TROPO_TRANSCRIPTION_REQUEST = '{"result":{"transcription":"%s","guid":"3a045980-edef-012e-7404-12313d064a99","identifier":null}}' % SAMPLE_VOICEMAIL_WORDS

TYPICAL_TROPO_AFTER_HANGUP_REQUEST = '{"result":{"sessionId":"ab2ca59771a2f330d088136c1003fdc3","callId":"30b550c16376c45659c5d15c20f6616c","state":"DISCONNECTED","sessionDuration":68,"sequence":2,"complete":true,"error":null,"actions":{"name":"conference-2750a4f1-6e27-4396-8538-807f3af313c6","duration":48,"disposition":"HANGUP"}}}'
