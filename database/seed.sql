-- =============================================================================
-- CECRMS — Sample Seed Data (v1.0.0)
-- Run AFTER schema.sql. Provides enough data to explore every feature
-- immediately: admin, coordinators, students, clubs, venues,
-- events, attendance, certificates, notifications, and Campus Connect
-- announcements.
--
-- Demo login credentials (also documented in README.md):
--   admin@cecrms.com        / admin123      (admin)
--   coord.robotics@cecrms.com / coord123    (club_admin — Robotics Club)
--   coord.music@cecrms.com    / coord123    (club_admin — Music Club)
--   asha@cecrms.com          / student123   (student)
--   ravi@cecrms.com          / student123   (student)
--   meera@cecrms.com         / student123   (student)
-- =============================================================================

USE cecrms;

-- ── Users ────────────────────────────────────────────────────────────────────
-- Password hashes below are real werkzeug (scrypt) hashes for the plaintext
-- passwords documented above — login works out of the box.
INSERT INTO users (name, email, password_hash, role, phone, club_id) VALUES
  ('System Admin', 'admin@cecrms.com',
   'scrypt:32768:8:1$y5O6TA5eTtoLnsFt$b28c15694b8d53893de12da48721aa9da83f93637615d174f62105575f21a5299011979ffabd1ef64777a670c25e9d504aebd93db0e3b17ed219613a2a87515c',
   'admin', '9000000001', NULL),
  ('Priya Nair', 'coord.robotics@cecrms.com',
   'scrypt:32768:8:1$6t8Ch3cTnPBubrd6$ff8f72663435d38e4d788c659f2aae0b1ad7dcbeb909fa6afd273554a1c4d807e859a854cb235391dee5f7870589c60fff4a65bd6b5f8c3e90adfad5c9c330a6',
   'club_admin', '9000000002', NULL),
  ('Karthik Rao', 'coord.music@cecrms.com',
   'scrypt:32768:8:1$6t8Ch3cTnPBubrd6$ff8f72663435d38e4d788c659f2aae0b1ad7dcbeb909fa6afd273554a1c4d807e859a854cb235391dee5f7870589c60fff4a65bd6b5f8c3e90adfad5c9c330a6',
   'club_admin', '9000000003', NULL),
  ('Asha Menon', 'asha@cecrms.com',
   'scrypt:32768:8:1$SuJncFttnA5BD3oP$940f89013f00ff4517335d74847147c1435f437b9f6a6ea985d3e34ef73eced7a1b3c8f91452344e0fef915cb4d29530da5ed58ddce0d2a19bd8c29076299cd4',
   'student', '9000000004', NULL),
  ('Ravi Kumar', 'ravi@cecrms.com',
   'scrypt:32768:8:1$SuJncFttnA5BD3oP$940f89013f00ff4517335d74847147c1435f437b9f6a6ea985d3e34ef73eced7a1b3c8f91452344e0fef915cb4d29530da5ed58ddce0d2a19bd8c29076299cd4',
   'student', '9000000005', NULL),
  ('Meera Iyer', 'meera@cecrms.com',
   'scrypt:32768:8:1$SuJncFttnA5BD3oP$940f89013f00ff4517335d74847147c1435f437b9f6a6ea985d3e34ef73eced7a1b3c8f91452344e0fef915cb4d29530da5ed58ddce0d2a19bd8c29076299cd4',
   'student', '9000000006', NULL);

-- ── Clubs (coordinator assigned after users exist) ──────────────────────────
INSERT INTO clubs (club_name, description, coordinator_id, assigned_at, assigned_by, club_email) VALUES
  ('Robotics Club', 'Building and competing with autonomous robots.',
   (SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com'),
   NOW(), (SELECT user_id FROM users WHERE email='admin@cecrms.com'),
   'coord.robotics@cecrms.com'),
  ('Music Club', 'Campus band, open mics, and music production workshops.',
   (SELECT user_id FROM users WHERE email='coord.music@cecrms.com'),
   NOW(), (SELECT user_id FROM users WHERE email='admin@cecrms.com'),
   'coord.music@cecrms.com'),
  ('Literary Society', 'Debates, creative writing, and book clubs.', NULL, NULL, NULL, NULL);

-- Reflect coordinator assignment on the users table (club_id = club they coordinate).
UPDATE users SET club_id = (SELECT club_id FROM clubs WHERE club_name='Robotics Club')
  WHERE email='coord.robotics@cecrms.com';
UPDATE users SET club_id = (SELECT club_id FROM clubs WHERE club_name='Music Club')
  WHERE email='coord.music@cecrms.com';

-- ── Club membership ──────────────────────────────────────────────────────────
INSERT INTO club_members (club_id, user_id, position) VALUES
  ((SELECT club_id FROM clubs WHERE club_name='Robotics Club'),
   (SELECT user_id FROM users WHERE email='asha@cecrms.com'), 'President'),
  ((SELECT club_id FROM clubs WHERE club_name='Robotics Club'),
   (SELECT user_id FROM users WHERE email='ravi@cecrms.com'), 'Member'),
  ((SELECT club_id FROM clubs WHERE club_name='Music Club'),
   (SELECT user_id FROM users WHERE email='meera@cecrms.com'), 'Secretary');

-- ── Venues ───────────────────────────────────────────────────────────────────
INSERT INTO venues (venue_name, capacity, location, type) VALUES
  ('Main Auditorium', 500, 'Block A, Ground Floor', 'Auditorium'),
  ('Seminar Hall 2', 120, 'Block B, 2nd Floor', 'Seminar Hall'),
  ('Open Air Theatre', 800, 'Central Lawn', 'Outdoor'),
  ('Robotics Lab', 40, 'Block C, 1st Floor', 'Lab');


-- ── Events ───────────────────────────────────────────────────────────────────
INSERT INTO events (club_id, title, description, event_lead, contact_no, venue_id,
                    date, start_time, end_time, registration_link, approved_status,
                    category, created_by) VALUES
  ((SELECT club_id FROM clubs WHERE club_name='Robotics Club'),
   'Robo Wars 2026', 'Annual robot combat competition open to all branches.',
   'Priya Nair', '9000000002',
   (SELECT venue_id FROM venues WHERE venue_name='Main Auditorium'),
   DATE_ADD(CURDATE(), INTERVAL 10 DAY), '10:00:00', '17:00:00',
   'https://forms.example.com/robowars', 'Approved', 'Technical',
   (SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com')),
  ((SELECT club_id FROM clubs WHERE club_name='Robotics Club'),
   'Intro to Arduino Workshop', 'Hands-on workshop for beginners.',
   'Priya Nair', '9000000002',
   (SELECT venue_id FROM venues WHERE venue_name='Robotics Lab'),
   DATE_SUB(CURDATE(), INTERVAL 5 DAY), '14:00:00', '16:30:00',
   NULL, 'Approved', 'Technical',
   (SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com')),
  ((SELECT club_id FROM clubs WHERE club_name='Music Club'),
   'Open Mic Night', 'Showcase your talent — singing, poetry, and more.',
   'Karthik Rao', '9000000003',
   (SELECT venue_id FROM venues WHERE venue_name='Open Air Theatre'),
   DATE_ADD(CURDATE(), INTERVAL 3 DAY), '18:00:00', '21:00:00',
   'https://forms.example.com/openmic', 'Approved', 'Cultural',
   (SELECT user_id FROM users WHERE email='coord.music@cecrms.com')),
  ((SELECT club_id FROM clubs WHERE club_name='Music Club'),
   'Battle of Bands (Pending Review)', 'Inter-college band competition proposal.',
   'Karthik Rao', '9000000003',
   (SELECT venue_id FROM venues WHERE venue_name='Main Auditorium'),
   DATE_ADD(CURDATE(), INTERVAL 25 DAY), '17:00:00', '22:00:00',
   NULL, 'Pending', 'Cultural',
   (SELECT user_id FROM users WHERE email='coord.music@cecrms.com'));

-- ── Attendance (for the past workshop) ──────────────────────────────────────
INSERT INTO attendance (event_id, user_id, scan_by) VALUES
  ((SELECT event_id FROM events WHERE title='Intro to Arduino Workshop'),
   (SELECT user_id FROM users WHERE email='asha@cecrms.com'),
   (SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com')),
  ((SELECT event_id FROM events WHERE title='Intro to Arduino Workshop'),
   (SELECT user_id FROM users WHERE email='ravi@cecrms.com'),
   (SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com'));

-- ── Certificates (issued for the attended workshop) ─────────────────────────
INSERT INTO certificates (event_id, user_id, issue_date, cert_path) VALUES
  ((SELECT event_id FROM events WHERE title='Intro to Arduino Workshop'),
   (SELECT user_id FROM users WHERE email='asha@cecrms.com'),
   CURDATE(), NULL);


-- ── Notifications ────────────────────────────────────────────────────────────
INSERT INTO notifications (user_id, title, body, link, type, event_key) VALUES
  ((SELECT user_id FROM users WHERE email='asha@cecrms.com'),
   'Certificate Ready', 'Your certificate for "Intro to Arduino Workshop" is ready.',
   '/certificates/my', 'success', 'seed_cert_1'),
  ((SELECT user_id FROM users WHERE email='ravi@cecrms.com'),
   'New Event: Robo Wars 2026', 'A new event has been approved for Robotics Club.',
   '/events/', 'info', 'seed_event_1');

-- ── Campus Connect announcements ─────────────────────────────────────────────
INSERT INTO cc_announcements (author_id, target_type, target_id, title, body, is_pinned) VALUES
  ((SELECT user_id FROM users WHERE email='admin@cecrms.com'),
   'everyone', NULL, 'Welcome to Campus Connect',
   'Chat with coordinators, get instant AI help, and never miss a club announcement again.',
   1),
  ((SELECT user_id FROM users WHERE email='coord.robotics@cecrms.com'),
   'club', (SELECT club_id FROM clubs WHERE club_name='Robotics Club'),
   'Robo Wars registrations open',
   'Team registrations for Robo Wars 2026 are now open — register before the deadline!',
   0);

SELECT 'CECRMS seed data inserted successfully.' AS status;
