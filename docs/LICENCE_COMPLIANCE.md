# Lyrics licence & compliance checklist

This document covers all licensing, legal, and compliance requirements
for publishing LyricFinder on the App Store and Google Play.

---

## Lyrics licensing

### Why this matters

Song lyrics are protected by copyright. Displaying them without a licence
is infringement regardless of how you obtained them. This applies to:
- Full lyrics in the app
- Lyrics cached on your server
- Lyrics in screenshots or marketing materials

### Approved providers

| Provider | Tier | Use case | Contact |
|---|---|---|---|
| **Musixmatch** | Commercial | Best coverage (>11M songs), SDK, API | developer.musixmatch.com |
| **LyricFind** | Commercial | Strong US/EU catalogue, curated data | lyricfind.com |
| **Genius** | Attribution-only | Display only, links back to Genius | docs.genius.com |

### Prototype mode (pre-licence)

Until a licence is signed, display **at most 4 lines** as an excerpt with:
```
© [Artist name] / [Composer]. Lyric excerpt via Musixmatch.
All rights reserved.
```

Never store full lyrics in your database without a licence.

### Musixmatch integration steps

1. Register at https://developer.musixmatch.com
2. Request a commercial licence (free tier = 2,000 calls/day, display restrictions)
3. Integrate the Musixmatch iOS/Android SDK or REST API
4. Display their required attribution badge in every lyrics view
5. Do not cache lyrics beyond their specified TTL

### LyricFind integration steps

1. Contact sales@lyricfind.com for a commercial agreement
2. Implement their API with required attribution
3. Never store lyrics server-side without explicit permission in the contract

---

## App Store compliance

### Apple App Store checklist

- [ ] **Privacy policy URL** — required, must describe: search query logging,
      analytics data, device identifiers, lyrics attribution
- [ ] **Support URL** — required
- [ ] **App privacy details** (App Store Connect → Privacy):
  - Data collected: Search history, Device ID (analytics)
  - Purpose: App functionality, Analytics
  - Not sold to third parties
- [ ] **Entitlements** verified: push notifications, microphone
- [ ] **Usage descriptions** (Info.plist):
  ```xml
  <key>NSMicrophoneUsageDescription</key>
  <string>LyricFinder uses your microphone for voice search.</string>
  <key>NSUserTrackingUsageDescription</key>
  <string>This allows us to improve the app experience.</string>
  ```
- [ ] **Age rating**: 4+ (no objectionable content)
- [ ] **TestFlight beta** completed before production submission
- [ ] **Screenshots** prepared:
  - 6.7" iPhone (1290×2796)
  - 6.1" iPhone (1179×2556)
  - 5.5" iPhone (1242×2208)
  - 12.9" iPad Pro (2048×2732)
- [ ] **App icon**: 1024×1024 PNG, no alpha, no rounded corners (Apple adds them)
- [ ] **Promotional text** (max 170 chars) — can be updated without review
- [ ] **Keywords** (max 100 chars): lyric, song, music, shazam, lyrics finder

### App Store review common rejections

- Missing privacy policy → add URL in App Store Connect before submission
- Microphone use without justification → add `NSMicrophoneUsageDescription`
- Full lyrics without licence → switch to excerpt mode
- Crashes on launch → run on physical device before submitting
- Login required for core functionality → search must work without account

---

## Google Play compliance

### Google Play checklist

- [ ] **Target SDK** ≥ 34 (Android 14) — required for new apps from 2024
- [ ] **AAB format** (not APK) for production submission
- [ ] **Play App Signing** enrolled
- [ ] **Content rating** questionnaire completed (Music & Audio)
- [ ] **Data safety section** (Play Console → Policy → App content):
  - Data collected: App interactions (searches), Device or other IDs
  - Data not sold
  - Users can request deletion
- [ ] **Privacy policy URL** — same as iOS or Play-specific
- [ ] **Feature graphic**: 1024×500 PNG
- [ ] **Screenshots** (phone + 7" + 10" tablet)
- [ ] **App icon**: 512×512 PNG
- [ ] **Short description** (max 80 chars)
- [ ] **Full description** (max 4000 chars) — include keywords naturally
- [ ] **Internal test → Closed → Open → Production** track progression
- [ ] **Release notes** (what's new) for each build

### Permissions justification

Declare in Play Console why each permission is needed:

| Permission | Justification |
|---|---|
| `INTERNET` | Required to call the search API and stream audio previews |
| `RECORD_AUDIO` | Optional voice search feature |
| `RECEIVE_BOOT_COMPLETED` | Resume background notifications after reboot |
| `POST_NOTIFICATIONS` | Notify users of saved song updates |

---

## GDPR / CCPA compliance

### Required

- [ ] **Consent modal** on first launch (EU users): explain data collected,
      allow reject-all option
- [ ] **Privacy policy** linked from: app store listing, in-app settings,
      consent modal
- [ ] **Data deletion** endpoint: users can request account + search history deletion
- [ ] **Data retention policy**: define how long search logs are kept (recommend 90 days)
- [ ] **Analytics opt-out**: Firebase Analytics respects `setAnalyticsCollectionEnabled(false)`
- [ ] **Crash reporting opt-out**: Sentry respects `enabled: false` in user preference

### Search query logging

Search queries may be personal data (e.g. "comme un petit coeur" is identifiable
to a specific user if linked to their account). Ensure:
- Logs are pseudonymised (store hash of device ID, not raw ID)
- Retention period defined and enforced (automated deletion job)
- Excluded from any data sharing with third parties

---

## Third-party SDK compliance

| SDK | Data collected | Opt-out mechanism |
|---|---|---|
| Firebase Analytics | App events, device info | `setAnalyticsCollectionEnabled(false)` |
| Sentry | Crash reports, device info | `Sentry.enabled = false` |
| RevenueCat | Purchase events | Delete user in RevenueCat dashboard |
| Spotify SDK | Auth token, playback events | Revoke Spotify permissions in Spotify settings |

---

## Contacts for licensing

| Organisation | Contact | Notes |
|---|---|---|
| Musixmatch | licensing@musixmatch.com | Start here for lyrics API |
| LyricFind | sales@lyricfind.com | Alternative/complement |
| SACEM (France) | droits@sacem.fr | French collecting society |
| PRS for Music (UK) | info@prsformusic.com | UK performing rights |
| ASCAP (USA) | info@ascap.com | US performing rights |
| BMI (USA) | licensing@bmi.com | US performing rights |
