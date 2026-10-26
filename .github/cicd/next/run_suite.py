import argparse
import json
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=['unit', 'api', 'integration'], required=True)
    parser.add_argument('--report-dir', default='/reports')
    args = parser.parse_args()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('test_'+args.suite)
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'suite': args.suite, 'discovered': discovered, 'executed': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'passed': discovered > 0 and result.wasSuccessful() and result.testsRun == discovered and not result.skipped,
              'details': [{'test': str(test), 'traceback': trace} for test, trace in result.failures+result.errors]}
    directory = Path(args.report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory/(args.suite+'.json')).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
