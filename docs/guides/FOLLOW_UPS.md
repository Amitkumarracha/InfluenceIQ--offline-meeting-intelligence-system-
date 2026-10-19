# Review tasks and export deadlines

Available in the website and Android **0.7.1-prototype**. Everything in the local Android workflow works offline. No new model or package is required. Editing a follow-up does not rerun transcription or speaker analysis.

## Website

1. Open a completed meeting and choose **Action items**.
2. Listen to the source, then choose **Review follow-up**.
3. Enter an owner if known, choose an exact due date if agreed, and select **Open**, **Done** or **Dismissed candidate**. Save.
4. Use **Meeting options → Export format → Reviewed task calendar (.ics) → Export** to save calendar reminders for reviewed open tasks with dates.

The task speaker is not automatically its owner. Relative expressions such as “kal”, “next Friday” or “अगले हफ्ते” are not silently converted into dates: confirm the intended date yourself. Empty owner/date fields remain unassigned. A dismissed candidate remains available with its original source; dismissal does not erase evidence.

## Android

Open **Action items → Review follow-up** or **Edit follow-up**. Owner is editable; tap the date field to choose a date, or **Clear due date** to remove it. Choose the status and save. Corrections stay on the device, independently of the account session, and remain available after restarting.

Open **Export → Reviewed task calendar** to save an `.ics` file through Android's document picker. Reviewed tasks also appear in Markdown and JSON exports. Original transcript and event text are unchanged.

Use **Publish to account** to send the reviewed report to the same account used by the website. Download its account copy to bring website reviews to Android. If the server changed since the last download/publication, publication is rejected until the newer copy is downloaded and reviewed. A newer downloaded revision becomes a separate device snapshot, preserving older local edits. See [Account & sync](ACCOUNT_SYNC.md).

## Calendar behavior

Only explicitly reviewed **open** tasks with valid dates are exported. Each is an all-day reminder, with the source task text, selected owner and recording offset in its description. It has no attendee list or invitation. The app writes a local file; you choose whether to import it into a calendar. Importing it into an online calendar can share its included meeting content with that calendar provider.

Calendar export is a file integration, not a live Google/Outlook connection or notification scheduler. Updating a task does not automatically update or remove an event you previously imported. Calendar clients differ in how they handle reimports; use their edit/delete controls as needed. Completed, dismissed, unreviewed and undated tasks are excluded from new exports. If none qualify, the app explains why instead of generating misleading reminders.

## Preserving review accuracy

Reviews are separate from source evidence and are bound to the event ID, exact task text and available source timestamp. When analysis changes that evidence, an old review is retained as history but is not displayed/exported as the review of the changed task. Web edits also check report revisions to reject stale saves. Historical tasks without event IDs require reanalysis before tracking is available.

These controls support human review; they do not prove that transcription, speaker attribution or task detection is correct. Use the [current run commands](RUN_CURRENT.md) and [Read.ai comparison and validation](../validation/27_READ_AI_COMPARISON_AND_FOLLOWUPS_2026_10_19.md).
