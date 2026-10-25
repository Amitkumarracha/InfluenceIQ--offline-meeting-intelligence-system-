// Run against an isolated local API: this creates a test account and meeting.
const { chromium } = require(process.env.MAI_PLAYWRIGHT || '../.runtime/browser/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const base = process.env.MAI_TEST_BASE_URL || 'http://127.0.0.1:18001';
  const directory = path.resolve('.runtime/validation/web-regression-20261025');
  const browser = await chromium.launch({ headless: true, channel: 'chromium', args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
    const errors = []; page.on('pageerror', error => { errors.push(error.message); console.error('Browser error:', error.message); });
    page.on('requestfailed', request => console.error('Request failed:', new URL(request.url()).pathname, request.failure()?.errorText));
    page.on('request', request => { if (request.url().includes('/analyze')) console.log('Upload request:', request.method(), request.url()); });
    await page.goto(base);
    const email = `web-regression-${Date.now()}@example.invalid`, password = 'Laptop-validation-2026';
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByLabel('Confirm password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Create Account', exact: true }).click();
    await page.getByRole('heading', { name: 'Capture the conversation.' }).waitFor();
    await page.getByLabel('Upload audio', { exact: true }).setInputFiles([
      path.join(directory, 'first.wav'), path.join(directory, 'second.wav')]);
    await page.getByText('2 file(s) ready · parts play in the order below', { exact: true }).waitFor();
    await page.getByLabel('Upload audio', { exact: true }).setInputFiles(path.join(directory, 'first.wav'));
    await page.getByText('2 file(s) ready · parts play in the order below', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Move second.wav up', exact: true }).click();
    await page.getByRole('button', { name: 'Move first.wav up', exact: true }).click();
    await page.getByLabel('Upload PPT', { exact: true }).setInputFiles(path.join(directory, 'first.pptx'));
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: 'Add more PPTs', exact: true }).click();
    await (await chooser).setFiles(path.join(directory, 'second.pptx'));
    await page.getByText('2 presentation(s) · slides are combined in this order', { exact: true }).waitFor();
    assert.equal(await page.getByText('first.pptx', { exact: true }).count(), 1);
    assert(await page.getByLabel('Upload PPT', { exact: true }).evaluate(element => getComputedStyle(element).display === 'none'));
    await page.getByLabel('Meeting title (optional)', { exact: true }).fill('Website regression meeting');
    await page.getByLabel('Expected speakers', { exact: true }).fill('4');
    await page.screenshot({ path: path.join(directory, 'uploads.png'), fullPage: true });
    const accepted = page.waitForResponse(response => new URL(response.url()).pathname === '/api/analyze' && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Analyse meeting', exact: true }).press('Enter');
    const response = await accepted;
    assert.equal(response.status(), 202, await response.text());
    const mid = (await response.json()).meeting_id;
    const token = await page.evaluate(() => localStorage.getItem('token'));
    const headers = { Authorization: `Bearer ${token}` };
    const stages = new Set(); let draftSeen = false, state, cachedProcessing = null;
    async function waitForReport() {
      const deadline = Date.now() + 300000;
      while (!await page.getByRole('button', { name: 'Transcript', exact: true }).isVisible()) {
        assert(Date.now() < deadline, 'Meeting did not complete in five minutes');
        const snapshot = await page.request.get(`${base}/api/meetings/${mid}`, { headers, maxRetries: 2 });
        assert.equal(snapshot.status(), 200);
        state = await snapshot.json();
        assert.notEqual(state.status, 'failed', state.error);
        if (!stages.has(state.stage)) { stages.add(state.stage); console.log('Stage:', state.stage); }
        if (state.preview?.transcript_segments?.length) {
          assert.equal(state.preview.transcript_segments[0].segment_id, 1);
          draftSeen = true;
        }
        await page.waitForTimeout(1000);
      }
      return (await (await page.request.get(`${base}/api/meetings/${mid}`, { headers, maxRetries: 2 })).json()).data;
    }
    const data = await waitForReport();
    assert(data.transcript_segments.length > 0);
    assert.equal(data.slides.length, 2);
    assert(Math.abs(data.meeting_overview.duration_s - 90) < .1);
    assert.equal(data.processing.keyword_event_scoring_version, 2);
    const ids = new Set(data.transcript_segments.map(segment => segment.segment_id));
    const slideIds = new Set(data.slides.map(slide => slide.slide_id));
    for (const event of data.event_timeline) assert(ids.has(event.source_segment_id));
    for (const segment of data.aligned_segments) if (segment.slide_id && segment.slide_id !== 'NO_CONFIDENT_SLIDE') assert(slideIds.has(segment.slide_id));
    const features = ['proposal_contribution', 'evidence_contribution', 'objection_contribution',
      'revision_contribution', 'decision_contribution', 'interaction_contribution', 'slide_grounded_contribution'];
    const weightKeys = ['proposal', 'evidence', 'objection', 'revision', 'decision', 'interaction', 'slide_grounding'];
    for (const person of data.influence) {
      const expected = features.reduce((sum, key, index) => sum + (person.features[key] || 0) * data.influence_method.weights[weightKeys[index]], 0);
      assert(Math.abs(expected - person.influence_score) < .00001);
    }
    for (const label of ['Overview', 'Transcript', 'Participants', 'Action items', 'Decisions', 'Influence', 'Events', 'Presentation']) {
      await page.getByRole('button', { name: label, exact: true }).click();
      assert(await page.locator('.report-page .panel').count());
    }
    await page.getByRole('button', { name: 'Participants', exact: true }).click();
    if (data.participants.length) {
      await page.getByRole('button', { name: 'Edit name & role', exact: true }).first().click();
      await page.getByLabel('Speaker name', { exact: true }).fill('Test Reviewer');
      await page.getByLabel('Meeting role', { exact: true }).fill('Reviewer');
      await page.getByRole('button', { name: 'Save speaker', exact: true }).click();
      await page.getByText('Your role label: Reviewer', { exact: true }).waitFor();
    }
    await page.getByRole('button', { name: 'Overview', exact: true }).click();
    if (data.participants.length) {
      await page.locator('summary').filter({ hasText: 'Review speaker separation' }).click();
      await page.getByLabel('Actual number of speakers', { exact: true }).fill('4');
      const rerun = page.waitForResponse(response => response.url().includes('/analyze-speakers'));
      await page.getByRole('button', { name: 'Reanalyse with this speaker count', exact: true }).click();
      assert.equal((await rerun).status(), 202);
      await page.getByLabel('Meeting processing', { exact: true }).waitFor();
      const cached = await waitForReport();
      cachedProcessing = cached.processing;
      assert.equal(cached.processing.asr_last_chunk_cached, true);
      assert.deepEqual(cached.transcript_segments, data.transcript_segments);
      console.log('Cached rerun timings:', JSON.stringify(cached.processing.stage_timings_seconds));
    }
    await page.getByLabel('Meeting vocabulary', { exact: true }).fill('InfluenceIQ, GPU');
    await page.getByRole('button', { name: 'Save vocabulary', exact: true }).click();
    await page.getByText('Vocabulary saved with this meeting.', { exact: true }).waitFor();
    await page.locator('.meeting-menu > summary').click();
    for (const format of ['json', 'md', 'txt', 'srt', 'vtt', 'csv']) {
      await page.getByLabel('Export format', { exact: true }).selectOption(format);
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Export', exact: true }).click();
      const file = await download;
      assert.equal(await file.failure(), null);
      assert(file.suggestedFilename().endsWith('.' + format));
      await file.saveAs(path.join(directory, 'export.' + format));
    }
    await page.locator('.meeting-menu > summary').click();
    for (const width of [360, 390, 960, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    await page.screenshot({ path: path.join(directory, 'results.png'), fullPage: true });
    await page.getByRole('button', { name: 'History', exact: true }).click();
    await page.getByRole('button', { name: /^Website regression meeting/ }).click();
    await page.getByRole('button', { name: 'Overview', exact: true }).waitFor();
    assert.equal(await page.getByLabel('Meeting vocabulary', { exact: true }).inputValue(), 'InfluenceIQ, GPU');
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await page.getByRole('heading', { name: 'Welcome back', exact: true }).waitFor();
    await page.getByLabel('Email', { exact: true }).fill(email.toUpperCase());
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByRole('heading', { name: 'Capture the conversation.' }).waitFor();
    assert.equal(await page.locator('.report-page').count(), 0);
    assert.deepEqual(errors, []);
    const summary = { status: 'passed', meeting_id: mid, draft_seen: draftSeen, stages: [...stages],
      audio_parts: 2, presentations: 2, transcript_passages: data.transcript_segments.length,
      participants: data.participants.length, events: data.event_timeline.length, decisions: data.decisions.length,
      influence_records: data.influence.length, timings: data.processing.stage_timings_seconds,
      elapsed_seconds: data.processing.elapsed_seconds, cached_elapsed_seconds: cachedProcessing?.elapsed_seconds,
      cached_stage_timings: cachedProcessing?.stage_timings_seconds, automatic_results: true, exports: 6, errors };
    await fs.writeFile(path.join(directory, 'live-results.json'), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary));
  } finally { await browser.close(); }
})().catch(error => {
  console.error(error.message.split('\nCall log:')[0]);
  console.error((error.stack || '').split('\n').filter(line => line.trim().startsWith('at ')).join('\n'));
  process.exit(1);
});
