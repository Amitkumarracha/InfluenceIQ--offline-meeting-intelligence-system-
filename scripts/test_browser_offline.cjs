// Foreground UI check with intercepted local fixtures; starts no web/API server.
const { chromium } = require(process.env.MAI_PLAYWRIGHT || '../.runtime/browser/node_modules/playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chromium', args: ['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
  try {
    const context = await browser.newContext({ permissions: ['microphone'], viewport: { width: 390, height: 844 }, serviceWorkers: 'block', acceptDownloads: true });
    const page = await context.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    let title = 'Large meeting', notes = null, summaryStatus = null, uploaded = false, meetingPolls = 0;
    const transcript = Array.from({ length: 215 }, (_, i) => ({ segment_id: i + 1, start: 7200 + i * 5, end: 7204 + i * 5, speaker: 'SPEAKER_00', text: `Report passage ${i + 1}. Asha will send Friday.` }));
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== '127.0.0.1') throw new Error('External browser request: ' + url.hostname);
      const json = body => route.fulfill({ json: body });
      if (url.pathname === '/api/health') return json({ asr_ready: true, asr_model: 'small', asr_models: ['small', 'medium'], summary_models: ['local-test'] });
      if (url.pathname === '/api/auth/register') return json({ token: 'fixture-token', email: 'local@example.invalid' });
      if (url.pathname === '/api/meetings') return json({ meetings: [{ id: 'demo', title, status: 'completed' }] });
      if (url.pathname === '/api/analyze') {
        const body = route.request().postDataBuffer().toString();
        assert(body.includes('name="model_size"\r\n\r\nmedium'));
        assert(body.includes('name="vocabulary"\r\n\r\nAsha'));
        uploaded = true; return route.fulfill({ status: 202, json: { meeting_id: 'demo' } });
      }
      if (url.pathname === '/api/meetings/demo' && uploaded && meetingPolls++ < 2) return json({id: 'demo', title, status: 'processing', stage: 'transcription', progress: {completed_seconds: 120, total_seconds: 600}, preview: {total_segments: 1, transcript_segments: [{segment_id: 1, start: 10, text: 'हमने बजट फाइनल कर दिया।'}], events: [{event_type: 'decision'}]}});
      if (url.pathname === '/api/meetings/demo') return json({ id: 'demo', title, status: 'completed', summary_status: summaryStatus, audio_url: null, data: { participants: [], action_items: [], processing: { speaker_separation: false }, transcript_segments: transcript, local_notes: notes } });
      if (url.pathname === '/api/meetings/demo/edit') { title = route.request().postDataJSON().title || title; return json({ status: 'saved' }); }
      if (url.pathname === '/api/meetings/demo/ask') return json({ answers: [], sources: [{ ...transcript[0], context: [transcript[0]] }], method: 'transcript_search', message: 'Matching passages.' });
      if (url.pathname === '/api/meetings/demo/summarize') {
        notes = { model: 'local-test', chunks: 4, rejected_items: 0, overview: [{ text: 'Cited meeting note', quote: transcript[214].text, source_segment_ids: [215], start: transcript[214].start }], decisions: [], action_items: [], open_questions: [] };
        summaryStatus = 'completed'; return route.fulfill({ status: 202, json: { status: 'queued' } });
      }
      if (url.pathname === '/api/meetings/demo/export') return route.fulfill({ contentType: 'text/markdown', body: '# Large meeting\nFull transcript\nReport passage 215.', headers: { 'Content-Disposition': 'attachment; filename="meeting.md"' } });
      if (url.pathname === '/api/search') return json({ results: [{ ...transcript[214], meeting_id: 'demo', title }] });
      const file = path.join(__dirname, '../frontend/dist', url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname));
      const contentType = file.endsWith('.js') ? 'application/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html';
      return route.fulfill({ body: await fs.readFile(file), contentType });
    });
    await page.goto('http://127.0.0.1:8000');
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    await page.locator('input[type=email]').fill('local@example.invalid');
    await page.locator('input[type=password]').fill('test-password');
    await page.getByRole('button', { name: 'Create Account', exact: true }).click();
    await page.getByRole('button', { name: 'Start Recording', exact: true }).click();
    await page.getByRole('button', { name: 'Pause recording', exact: true }).waitFor();
    await page.waitForTimeout(5500); // Let MediaRecorder produce a real persisted chunk.
    await page.getByRole('button', { name: 'Pause recording', exact: true }).click();
    await page.getByRole('button', { name: 'Resume recording', exact: true }).click();
    await page.getByRole('button', { name: 'Stop & Save', exact: true }).click();
    await page.getByRole('button', { name: 'Recover recording', exact: true }).waitFor();
    await page.reload();
    await page.getByRole('button', { name: 'Recover recording', exact: true }).click();
    await page.getByText('1 file(s) ready', { exact: true }).waitFor();
    await page.getByText('Transcription settings', { exact: true }).click();
    await page.getByLabel('Speech model', { exact: true }).selectOption('medium');
    await page.getByLabel('Names and technical vocabulary', { exact: true }).fill('Asha');
    await page.getByRole('button', { name: 'Transcribe & analyse locally', exact: false }).click();
    await page.getByText('Latest saved transcript — draft', {exact: true}).waitFor();
    await page.getByText('हमने बजट फाइनल कर दिया।', {exact: false}).waitFor();
    await page.getByRole('heading', { name: 'Large meeting', exact: true }).waitFor();
    assert(uploaded);
    await page.getByRole('button', { name: 'Full Transcript', exact: true }).click();
    await page.getByText('Transcript page 1 · 100 passages per page', { exact: true }).waitFor();
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.getByRole('button', { name: 'Play this transcript passage', exact: true }).count(), 215);
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByText(transcript[214].text, { exact: true }).waitFor();
    assert(await page.getByRole('button', { name: 'Next', exact: true }).isDisabled());
    await page.getByPlaceholder('Search transcript...').fill('Report passage 215.');
    await page.getByText('Transcript page 1 · 100 passages per page', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Generate notes', exact: true }).click();
    await page.getByText('Cited meeting note', { exact: true }).waitFor();
    await page.getByLabel('Question about this meeting').fill('Friday');
    await page.getByRole('button', { name: 'Ask meeting', exact: true }).click();
    await page.getByText('Matching passages.', { exact: true }).waitFor();
    await page.getByLabel('Export format').selectOption('md');
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export', exact: true }).click();
    const download = await downloaded;
    assert.equal(download.suggestedFilename(), 'demo_report.md');
    const width = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert(width.page <= width.viewport, JSON.stringify(width));
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ browser: 'passed', microphone: 'synthetic', recordingRecovery: true, pauseResume: true, settingsUpload: true, pagination: true, partialTranscript: true, notes: 'mocked', download: true, width, errors }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
