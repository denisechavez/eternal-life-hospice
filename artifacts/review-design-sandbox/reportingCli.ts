import { buildBrevoReport } from './brevoReportingPlugin';
import { buildReport as buildGoogleReport } from './liveReportingPlugin';
import { buildReport as buildWhatConvertsReport } from './whatConvertsReportingPlugin';

const source = process.argv[2];
const period = process.argv[3] ?? 'last28';

try {
  const report = source === 'google'
    ? await buildGoogleReport(period)
    : source === 'whatconverts'
      ? await buildWhatConvertsReport()
      : source === 'brevo'
        ? await buildBrevoReport()
        : null;

  if (!report) {
    throw new Error('Unknown Growth Intelligence reporting source.');
  }

  process.stdout.write(JSON.stringify(report));
} catch (error) {
  process.stdout.write(JSON.stringify({
    live: false,
    errors: [error instanceof Error ? error.message : 'Unable to load reporting data.'],
  }));
  process.exitCode = 1;
}