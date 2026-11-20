"""Regression: new-protocol analysis must never merge v1 and v3 trials."""
import json
import tempfile
import unittest
from pathlib import Path
from individual_analysis import audit, write_json
from test_individual_analysis import fixture


class ProtocolAnalysisTests(unittest.TestCase):
    def test_v3_supported_and_mixed_protocol_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'run';fixture(p)
            fs=sorted((p/'trials').glob('*.json'))
            for i,f in enumerate(fs):
                t=json.loads(f.read_text());payload=json.loads(t['payload'])
                schema=payload['response_format']['json_schema']['schema']
                schema['properties']={'explanation':{'type':'string'},'decision':{'type':'string'}}
                schema['required']=['explanation','decision']
                t['payload']=json.dumps(payload);write_json(f,t)
                if i==0:
                    with self.assertRaisesRegex(ValueError,'Mixed response protocols'):audit(p,True)
            self.assertEqual(audit(p,True)['mode'],'synthetic_test')


if __name__=='__main__':unittest.main()
