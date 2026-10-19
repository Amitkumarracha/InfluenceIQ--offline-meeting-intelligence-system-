// Local, intercepted fixtures: verifies the simple workflow without starting a server.
const { chromium } = require(process.env.MAI_PLAYWRIGHT || '../.runtime/browser/node_modules/playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const http = require('node:http');
(async () => {
  // Chromium worklet module fetches bypass Playwright interception. Serve this one local asset.
  const server = http.createServer(async (request, response) => {
    if (request.url !== '/recording-preview.js') { response.writeHead(404); return response.end(); }
    response.setHeader('Content-Type', 'application/javascript');
    response.end(await fs.readFile(path.join(__dirname, '../frontend/dist/recording-preview.js')));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, channel: 'chromium', args: ['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
  try {
    const context = await browser.newContext({ permissions: ['microphone'], viewport: { width: 390, height: 844 }, serviceWorkers: 'block', acceptDownloads: true });
    const page = await context.newPage(), errors = [];
    page.on('pageerror', e => errors.push(e.message));
    let title = 'Planning meeting', profile = { name: '', role: '', organization: '' }, uploaded = false, polls = 0;
    const transcript = Array.from({ length: 215 }, (_, i) => ({ segment_id: i + 1, start: 7200 + i * 5, end: 7204 + i * 5, speaker: 'SPEAKER_00', text: `Report passage ${i + 1}. Asha will send Friday.` }));
    const data = { transcript_segments: transcript, vocabulary: '', vocabulary_suggestions: ['budget', 'हिंदी'], participants: [{ speaker_id: 'SPEAKER_00', roles: ['evidence_provider'], influence_score: .7 }], action_items: [{ event_id: 'e1', text: 'I will send the report Friday.', speaker: 'SPEAKER_00', timestamp: '02:00:00', timestamp_s: 7200 }], decisions: [{ decision_id: 'd1', status: 'confirmed', final_decision_text: 'We decided to approve the budget.', supporting_segments: [1] }], processing: { speaker_separation: true }, language_analysis: { label: 'Possible Hindi–English mix', asr_languages: ['en', 'hi'] }, influence: [{ participant: 'SPEAKER_00', influence_score: .7, features: { evidence_contribution: 1 }, raw_features: { evidence_contribution: 2 }, explanation: ['Provided observed evidence.'], supporting_events: ['e1'] }], influence_method: { weights: { evidence: .2 } }, event_timeline: [{ event_id: 'e1', source_segment_id: 1, event_type: 'evidence', start: 7200, speaker: 'SPEAKER_00', text: 'Source budget evidence', slide_id: 'slide_01' }], slides: [{ slide_id: 'slide_01', slide_number: 1, title: 'Budget', text: ['Budget facts'], tables: [] }], aligned_segments: [{ segment_id: 1, speaker: 'SPEAKER_00', slide_id: 'slide_01', start: 7200, text: 'Linked slide discussion', alignment_score: .8 }], consistency_checks: { flags: [{ slide_id: 'slide_01', statement: 'Latency 120 ms', slide_text: 'Latency 100 ms', start: 7200, spoken_value: '120', slide_value: '100', unit: 'ms' }] }, meeting_overview: { duration_s: 8275 } };
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== '127.0.0.1') throw new Error('Unexpected external request');
      const json = body => route.fulfill({ json: body });
      if (url.pathname === '/api/recording/preview') return json({ segments: [{start: 0, end: 1, text: 'Live नमस्ते team', speaker: 'UNKNOWN'}], language: 'hi', draft: true });
      if (url.pathname === '/api/health') return json({ asr_ready: true, asr_model: 'small', asr_models: ['small', 'medium'], diarization: { ready: true, message: 'Local speaker models are ready.' }, generative_ai: false });
      if (url.pathname === '/api/auth/register') return json({ token: 'fixture-token', email: 'local@example.invalid' });
      if (url.pathname === '/api/auth/me') return json({ user_id: 'fixture-user', email: 'local@example.invalid' });
      if (url.pathname === '/api/profile') { if (route.request().method() === 'POST') profile = route.request().postDataJSON(); return json(profile); }
      if (url.pathname === '/api/meetings') return json({ meetings: [{ id: 'demo', title, status: 'completed', created_at: '2026-10-07T12:00:00' }] });
      if (url.pathname === '/api/analyze') {
        const body = route.request().postDataBuffer().toString();
        for (const value of ['name="model_size"\r\n\r\nmedium', 'name="language"\r\n\r\nauto', 'name="vocabulary"\r\n\r\nAsha', 'slides.pptx']) assert(body.includes(value), value);
        uploaded = true; return route.fulfill({ status: 202, json: { meeting_id: 'demo' } });
      }
      if (url.pathname === '/api/meetings/demo' && uploaded && polls++ < 1) return json({ id: 'demo', title, status: 'processing', stage: 'transcription', progress: { completed_seconds: 120, total_seconds: 600, elapsed_seconds: 42, stage_elapsed_seconds: 40, overall_percent: 11, stage_percent: 20, estimated_remaining_seconds: 300 }, preview: { transcript_segments: [{ segment_id: 1, start: 10, text: 'हमने बजट फाइनल कर दिया।' }] } });
      if (url.pathname === '/api/meetings/demo') return json({ id: 'demo', title, status: 'completed', data: { speaker_names: { SPEAKER_00: 'Imported Asha' }, ...data }, audio_url: null });
      if (url.pathname === '/api/meetings/demo/edit') { const changes = route.request().postDataJSON(); title = changes.title || title; Object.assign(data, changes); return json({ status: 'saved' }); }
      if (url.pathname === '/api/meetings/demo/export') return route.fulfill({ contentType: 'text/markdown', body: '# Planning meeting\nAsha: Reviewer\nReport passage 215.', headers: { 'Content-Disposition': 'attachment; filename="meeting.md"' } });
      assert(!url.pathname.includes('/ask') && !url.pathname.includes('/summarize') && url.pathname !== '/api/search', 'No generative or cross-transcript search requests');
      const file = path.join(__dirname, '../frontend/dist', url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname));
      return route.fulfill({ body: await fs.readFile(file), contentType: file.endsWith('.js') ? 'application/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html' });
    });
    const screenshots = path.join(__dirname, '../.runtime/validation/minimal-ui'); await fs.mkdir(screenshots, { recursive: true });
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    await page.getByLabel('Email', { exact: true }).fill('local@example.invalid'); await page.getByLabel('Password', { exact: true }).fill('test-password');
    await page.getByLabel('Confirm password', { exact: true }).fill('different-password');
    await page.getByRole('button', { name: 'Create Account', exact: true }).click();
    await page.getByText('Passwords do not match.', { exact: true }).waitFor();
    await page.getByLabel('Confirm password', { exact: true }).fill('test-password');
    await page.getByRole('button', { name: 'Create Account', exact: true }).click();
    await page.getByRole('heading', { name: 'Capture the conversation.' }).waitFor();
    assert.equal(await page.getByText('Speech model', { exact: true }).count(), 0);
    await page.screenshot({ path: path.join(screenshots, 'home.png'), fullPage: true });
    await page.getByRole('button', { name: /^Record meeting/ }).click();
    await page.getByRole('button', { name: 'Pause recording', exact: true }).waitFor(); await page.getByText('Live नमस्ते team', { exact: false }).waitFor({ timeout: 25000 }).catch(async error => { console.error(await page.getByLabel('Live transcription', {exact:true}).innerText(), errors); throw error; });
    await page.getByRole('button', { name: 'Pause recording', exact: true }).click(); await page.getByRole('button', { name: 'Resume recording', exact: true }).click();
    await page.getByRole('button', { name: 'Stop & Save', exact: true }).click(); await page.getByRole('button', { name: 'Recover recording', exact: true }).waitFor();
    await page.reload(); await page.getByRole('button', { name: 'Recover recording', exact: true }).click();
    await page.getByText('1 file(s) ready · parts play in the order below', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Name', { exact: true }).fill('Asha'); await page.getByRole('button', { name: 'Save profile', exact: true }).click();
    await page.getByText('Profile saved.', { exact: true }).waitFor(); assert.equal(profile.name, 'Asha');
    await page.getByLabel('Language', { exact: true }).selectOption('hi'); await page.reload();
    await page.getByRole('button', { name: 'Settings', exact: true }).click(); assert.equal(await page.getByLabel('Language', { exact: true }).inputValue(), 'hi');
    await page.getByLabel('Language', { exact: true }).selectOption('auto'); await page.getByText('Advanced audio settings', { exact: true }).click();
    await page.getByLabel('Speech model', { exact: true }).selectOption('medium');
    await page.screenshot({ path: path.join(screenshots, 'settings.png'), fullPage: true });
    await page.getByRole('button', { name: 'Home', exact: true }).click(); await page.getByRole('button', { name: 'Recover recording', exact: true }).click();
    await page.getByLabel('Upload PPT', { exact: true }).setInputFiles({ name: 'slides.pptx', mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', buffer: Buffer.from('presentation fixture') });
    assert.equal(await page.getByText('slides.pptx', { exact: true }).count(), 1);
    assert(await page.getByLabel('Upload PPT', { exact: true }).evaluate(element => element.classList.contains('visually-hidden')));
    await page.locator('summary').filter({ hasText: 'Vocabulary hints' }).click(); await page.getByLabel('Vocabulary hints', { exact: true }).fill('Asha');
    await page.getByRole('button', { name: 'Analyse meeting', exact: true }).click();
    await page.getByText(/हमने बजट फाइनल कर दिया।/).waitFor();
    await page.getByRole('progressbar', { name: 'Overall processing progress', exact: true }).waitFor();
    await page.getByText('11%', { exact: true }).waitFor();
    await page.screenshot({ path: path.join(screenshots, 'processing.png'), fullPage: true });
    await page.getByRole('button', { name: 'Transcript', exact: true }).waitFor(); assert(uploaded);
    await page.getByRole('button', { name: 'Transcript', exact: true }).click();
    await page.locator('.passage-heading strong').filter({ hasText: 'Imported Asha' }).first().waitFor();
    await page.getByRole('button', { name: 'Overview', exact: true }).click();
    await page.getByRole('button', { name: 'budget', exact: true }).click(); await page.getByLabel('Meeting vocabulary', { exact: true }).fill('Asha, हिंदी');
    await page.getByRole('button', { name: 'Save vocabulary', exact: true }).click(); await page.getByText('Vocabulary saved with this meeting.', { exact: true }).waitFor();
    assert.equal(data.vocabulary, 'Asha, हिंदी');
    await page.getByRole('button', { name: 'Action items', exact: true }).click(); await page.getByText('I will send the report Friday.', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Decisions', exact: true }).click(); await page.getByText('We decided to approve the budget.', { exact: true }).waitFor();
    await page.screenshot({ path: path.join(screenshots, 'decisions.png'), fullPage: true });
    await page.getByRole('button', { name: 'Participants', exact: true }).click(); await page.getByText('Estimated roles: evidence provider', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Edit name & role', exact: true }).click(); await page.getByLabel('Speaker name', { exact: true }).fill('Asha'); await page.getByLabel('Meeting role', { exact: true }).fill('Reviewer'); await page.getByRole('button', { name: 'Save speaker', exact: true }).click(); await page.getByText('Your role label: Reviewer', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'History', exact: true }).click(); await page.getByRole('button', { name: /^Planning meeting/ }).click();
    await page.getByRole('button', { name: 'Participants', exact: true }).click(); await page.getByText('Your role label: Reviewer', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Home', exact: true }).click(); await page.getByRole('heading', { name: 'Capture the conversation.' }).waitFor();
    await page.getByRole('button', { name: 'History', exact: true }).click(); await page.getByRole('button', { name: /^Planning meeting/ }).click();
    await page.getByRole('button', { name: 'Transcript', exact: true }).click(); await page.getByRole('button', { name: 'Next', exact: true }).click(); await page.getByRole('button', { name: 'Next', exact: true }).click(); await page.getByText(transcript[214].text, { exact: true }).waitFor();
    await page.getByLabel('Search transcript', { exact: true }).fill('Report passage 215.'); await page.locator('mark').filter({ hasText: 'Report passage 215.' }).waitFor(); assert.equal(await page.getByRole('button', { name: 'Play this transcript passage', exact: true }).count(), 1);
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint'))); assert.equal(await page.getByRole('button', { name: 'Play this transcript passage', exact: true }).count(), 215); await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await page.getByRole('button', { name: 'Transcript', exact: true }).click(); await page.getByText('Reviewer', { exact: true }).first().waitFor();
    await page.getByRole('button', { name: 'Influence', exact: true }).click(); await page.getByText('0.70 / 1', { exact: true }).waitFor();
    await page.getByText('Score breakdown & evidence', { exact: true }).click(); await page.getByText('Source budget evidence', { exact: true }).waitFor();
    await page.screenshot({ path: path.join(screenshots, 'influence.png'), fullPage: true });
    await page.getByRole('button', { name: 'Presentation', exact: true }).click(); await page.getByText('Linked discussion', { exact: true }).click(); await page.getByText('Linked slide discussion', { exact: true }).waitFor(); await page.getByText('Spoken 120 vs slide 100 ms', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Events', exact: true }).click(); await page.getByText('Source budget evidence', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'History', exact: true }).click(); assert.equal(await page.getByRole('button', { name: 'Search inside transcripts' }).count(), 0); await page.getByRole('button', { name: /^Planning meeting/ }).click();
    assert.equal(await page.getByText('Notes & questions').count(), 0);
    await page.locator('summary').filter({ hasText: 'Meeting options' }).click(); const downloadEvent = page.waitForEvent('download'); await page.getByRole('button', { name: 'Export', exact: true }).click(); assert.equal((await downloadEvent).suggestedFilename(), 'demo_report.md');
    for (const width of [360, 390, 960, 1440]) {
      await page.setViewportSize({ width, height: 900 }); const actual = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth })); assert(actual.page <= actual.viewport, JSON.stringify(actual));
    }
    await page.screenshot({ path: path.join(screenshots, 'desktop-report.png'), fullPage: true });
    await page.getByRole('button', { name: 'Home', exact: true }).click();
    await page.screenshot({ path: path.join(screenshots, 'desktop-home.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ browser: 'passed', microphone: 'synthetic', recordingRecovery: true, liveMicrophonePreview: true, settingsPersistence: true, profile: true, pptUpload: true, vocabularyEdits: true, speakerEditsAndHistory: true, resultTabs: true, paginationAndPrint: true, generativeFeaturesRemoved: true, transcriptRoleLabels: true, influenceEvidence: true, presentationAlignment: true, export: true, widths: [360, 390, 960, 1440], progressAndAutomaticResults: true, importedSpeakerNames: true, searchHighlight: true, passwordConfirmation: true, errors }));
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exit(1); });
