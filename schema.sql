-- schema.sql
CREATE DATABASE IF NOT EXISTS cecrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cecrms;

-- USERS
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('Coordinator','Co-Coordinator','Co-Coordinator-Ops','Co-Coordinator-PR','Co-Coordinator-Finance','Student') DEFAULT 'Student',
  phone VARCHAR(20),
  club_id INT DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CLUBS
CREATE TABLE clubs (
  club_id INT AUTO_INCREMENT PRIMARY KEY,
  club_name VARCHAR(150) NOT NULL,
  description TEXT,
  coordinator_id INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (coordinator_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- VENUES
CREATE TABLE venues (
  venue_id INT AUTO_INCREMENT PRIMARY KEY,
  venue_name VARCHAR(150) NOT NULL,
  capacity INT DEFAULT 0,
  location VARCHAR(255)
);

-- RESOURCES
CREATE TABLE resources (
  resource_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  stock INT DEFAULT 0,
  description TEXT
);

-- Venues
CREATE TABLE venues (
    venue_id INT AUTO_INCREMENT PRIMARY KEY,
    venue_name VARCHAR(100) NOT NULL,
    capacity INT DEFAULT NULL
);


-- EVENTS (note: registration_link is here; event_lead & contact_no added)
CREATE TABLE events (
  event_id INT AUTO_INCREMENT PRIMARY KEY,
  club_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  event_lead VARCHAR(150),
  contact_no VARCHAR(30),
  venue_id INT,
  date DATE,
  start_time TIME,
  end_time TIME,
  poster VARCHAR(255),
  registration_link VARCHAR(1024), -- link to google form
  approved_status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
  created_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
  FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- RESOURCE ALLOCATION
CREATE TABLE resource_allocations (
  alloc_id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  resource_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  approved_by INT,
  status ENUM('Requested','Approved','Rejected') DEFAULT 'Requested',
  requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE,
  FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- ATTENDANCE (no registration table; students log-in and generate QR to be scanned)
CREATE TABLE attendance (
  attendance_id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  user_id INT NOT NULL,
  scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  scan_by INT DEFAULT NULL, -- id of the staff/volunteer who scanned (optional)
  UNIQUE KEY unique_attendance (event_id, user_id),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (scan_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- CERTIFICATES
CREATE TABLE certificates (
  cert_id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  user_id INT NOT NULL,
  issue_date DATE,
  cert_path VARCHAR(255),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- USER ACTIVITY (for recommender)
CREATE TABLE user_activity (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  event_id INT NOT NULL,
  interaction_type ENUM('viewed','clicked','attended') NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

CREATE TABLE event_resources (
    er_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    resource_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
);

