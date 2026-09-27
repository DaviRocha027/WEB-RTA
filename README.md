# WEB-RTA — Web Application Security Write-up

> **Web Application Security | Pentest | Red Team | Vulnerability Research**

Write-up documenting my approach to solving a **WEB-RTA** challenge, including reconnaissance, enumeration, vulnerability identification, exploitation and attack chaining.

The objective of this write-up is not only to document the vulnerabilities found, but also to demonstrate the **reasoning and methodology used throughout the assessment**.

---

## ⚠️ Disclaimer

This repository was created for **educational and portfolio purposes**.

All testing described here was performed against an authorized training environment.

Credentials, session tokens, cookies and other sensitive authentication data have been intentionally removed or masked from the public version.

---

# Table of Contents

* [Overview](#overview)
* [Methodology](#methodology)
* [Attack Chain](#attack-chain)
* [1. JWT Analysis](#1-jwt-analysis)
* [2. Endpoint Enumeration](#2-endpoint-enumeration)
* [3. SQL Injection](#3-sql-injection)
* [4. XXE](#4-xxe)
* [5. SSRF](#5-ssrf)
* [6. Data Decoding](#6-data-decoding)
* [7. Second Application](#7-second-application)
* [8. OAuth Scope Manipulation](#8-oauth-scope-manipulation)
* [9. OTP Enumeration](#9-otp-enumeration)
* [10. Administrative Access](#10-administrative-access)
* [Vulnerabilities Identified](#vulnerabilities-identified)
* [Tools Used](#tools-used)
* [Key Takeaways](#key-takeaways)

---

# Overview

The challenge involved two interconnected web applications.

The initial application contained several vulnerabilities that could be chained together to obtain access to an internal service and retrieve information required to access the second application.

The final attack chain involved:

* JWT manipulation
* Authorization flaws
* SQL Injection
* XXE
* SSRF
* Internal service access
* Data decoding
* OAuth scope manipulation
* Weak OTP implementation
* OTP brute-force

The overall exploitation path was:

```text
JWT Analysis
     │
     ▼
Role Manipulation
     │
     ▼
User Enumeration
     │
     ▼
SQL Injection
     │
     ▼
Authentication Bypass
     │
     ▼
Administrative Access
     │
     ├───────────────┐
     ▼               ▼
    XXE             SSRF
                      │
                      ▼
             Internal Service
                      │
                      ▼
              Encoded Data
                      │
                      ▼
                 Credentials
                      │
                      ▼
             Second Application
                      │
                      ▼
              OAuth Scope Abuse
                      │
                      ▼
                  OTP Check
                      │
                      ▼
               OTP Enumeration
                      │
                      ▼
            Administrative Access
                      │
                      ▼
                 Final Flag
```

---

# Methodology

I followed a structured approach throughout the challenge:

```text
Reconnaissance
      ↓
Enumeration
      ↓
Identify attack surface
      ↓
Form hypothesis
      ↓
Validate hypothesis
      ↓
Exploit
      ↓
Analyze result
      ↓
Use obtained information
      ↓
Continue exploitation
```

One of the main objectives was to avoid treating each vulnerability as an isolated finding.

Instead, information obtained from one vulnerability was used to guide the next stage of the assessment.

---

# 1. JWT Analysis

I started the assessment by intercepting application traffic using **Burp Suite**.

During the initial inspection, I identified a **JSON Web Token (JWT)** being used by the application.

After decoding the token with JWT.io, I observed:

```text
alg: none
```

The payload also contained:

```text
role: anonymous
```

The ability to modify these values immediately raised a concern regarding the application's authorization mechanism.

### Hypothesis

The application could potentially be trusting client-controlled JWT claims when making authorization decisions.

I therefore started testing whether modifying the `role` parameter would affect the application's behavior.

---

# 2. Endpoint Enumeration

I performed endpoint enumeration and identified:

```text
/login
/logout/
/dashboard
/admin/events
```

An interesting behavior was observed when accessing:

```text
/dashboard
```

without authenticating.

The application returned a page that appeared to belong to an authenticated area.

I then tested different values for the JWT `role`.

Changing the value to:

```text
administrator
```

or:

```text
admin
```

did not provide the expected access.

However, setting:

```text
role=user
```

caused the application to return event information.

One of the returned events contained:

```text
Masquerade Ball,user

Super Fun Event

Happening at: 2051-12-31 10:00

Created by: notatypicalsysadmin
```

This exposed a valid-looking username:

```text
notatypicalsysadmin
```

This information became useful for the next stage.

---

# 3. SQL Injection

With the username identified, I moved to:

```text
/login
```

Based on the application's behavior, I tested the authentication mechanism for SQL Injection.

The payload that successfully bypassed authentication was:

```text
notatypicalsysadmin' or 1=1--
```

The injection allowed me to bypass the login mechanism.

After authentication, I gained access to administrative functionality, including:

```text
/admin/events
/fetch_internal_secret
```

### Finding

**SQL Injection — Authentication Bypass**

The login functionality was vulnerable to SQL Injection, allowing authentication to be bypassed through manipulation of the underlying database query.

---

# 4. XXE

After obtaining administrative access, I continued testing the functionality available under:

```text
/admin/events
```

I identified the following endpoint:

```text
/admin/events/update/1
```

The endpoint processed XML input.

This immediately raised the possibility of an **XML External Entity (XXE)** vulnerability.

I tested the following payload:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY conteudo SYSTEM "file:///etc/passwd">
]>
<event>
  <title>&conteudo;</title>
  <description>Super Fun Event</description>
  <happening_at>2051-12-31 10:00</happening_at>
  <visibility>user</visibility>
</event>
```

The test attempted to reference:

```text
/etc/passwd
```

through an external XML entity.

### Finding

**XML External Entity (XXE)**

The XML parser allowed external entities to be processed, creating the possibility of local file access through malicious XML input.

---

# 5. SSRF

I then analyzed:

```text
/fetch_internal_secret
```

particularly the functionality responsible for fetching the service status.

The application appeared to make an HTTP request based on user-controlled input.

This raised the possibility of **Server-Side Request Forgery (SSRF)**.

To validate this, I supplied an encoded loopback address:

```text
http%3A%2F%2F127%2E0%2E0%2E1%253A8000
```

The server processed the request and returned:

```text
requested_uri:
http://127.0.0.1:8000/secret
```

The response also indicated:

```text
status: success
status_code: 200
```

This confirmed that the application was performing the request from the server side.

### Finding

**Server-Side Request Forgery (SSRF)**

The application allowed user-controlled input to influence server-side HTTP requests, enabling access to an internal service bound to the loopback interface.

---

# 6. Data Decoding

The internal service returned a value stored in:

```text
hidden_in_layers
```

The data appeared as hexadecimal values:

```text
64 58 4e 6c 63 6c 38 30 5a 6d 49 33 4f 44 51 35 ...
```

I recognized that the values represented hexadecimal-encoded ASCII data.

After converting the hexadecimal values, another encoded string was obtained.

Further decoding revealed credentials required to access the second application.

### Methodology

The process was essentially:

```text
Hexadecimal
    ↓
ASCII
    ↓
Encoded string
    ↓
Decoded credentials
```

For security reasons, the credentials obtained during the challenge are not included in this public repository.

---

# 7. Second Application

Using the information obtained from the internal service, I moved to the second application.

During enumeration, I identified:

```text
/client/login
```

Using the previously obtained credentials, I successfully authenticated.

The application assigned the following client identity:

```text
client_1337
```

However, the initial authorization scope was limited to read-only access.

This indicated that the authorization mechanism was the next area worth investigating.

---

# 8. OAuth Scope Manipulation

I analyzed the authentication requests using **Burp Suite**.

During the inspection, I identified the authorization scope.

The original scope was:

```text
read
```

I modified it to:

```text
admin
```

The application accepted the modified value and redirected the authentication flow to:

```text
/oauth/otp
```

This behavior suggested that the server was not properly validating whether the requested scope was actually authorized for the client.

### Finding

**Authorization / OAuth Scope Manipulation**

A client with a read-only scope was able to request an administrative scope by modifying a client-controlled parameter.

---

# 9. OTP Enumeration

After modifying the scope, the application requested a three-digit OTP.

The available search space was therefore:

```text
000 - 999
```

This resulted in only:

```text
1,000 possible combinations
```

I automated the requests using a Python script to test the possible OTP values.

An alternative approach would be using **Burp Suite Intruder** with a numeric payload list.

The application did not appear to implement sufficient protection against repeated OTP attempts.

This made it possible to enumerate the valid OTP.

### Finding

**Weak OTP / Missing Brute-Force Protection**

The authentication mechanism relied on a three-digit OTP without sufficient protection against repeated attempts.

---

# 10. Administrative Access

After identifying the valid OTP, I completed the authentication flow.

The application granted administrative access.

From this point, I was able to access additional system information and complete the remaining objectives of the challenge.

The final stage resulted in the discovery of the **last flag**, completing the WEB-RTA challenge.

---

# Vulnerabilities Identified

| #  | Vulnerability                  | Impact                                            |
| -- | ------------------------------ | ------------------------------------------------- |
| 01 | JWT `alg: none`                | Token manipulation / authorization weakness       |
| 02 | Authorization flaw             | Client-controlled role affected access            |
| 03 | SQL Injection                  | Authentication bypass                             |
| 04 | XXE                            | Potential local resource/file access              |
| 05 | SSRF                           | Access to internal services                       |
| 06 | Information Disclosure         | Sensitive information exposed by internal service |
| 07 | OAuth Scope Manipulation       | Unauthorized privilege escalation                 |
| 08 | Weak OTP                       | Reduced authentication security                   |
| 09 | Missing Brute-Force Protection | OTP could be systematically enumerated            |

---

# Attack Chain Analysis

The most interesting aspect of this challenge was not any individual vulnerability, but the way the vulnerabilities could be chained together.

The initial JWT issue provided additional application information.

That information led to a valid username.

The username enabled SQL Injection testing, which resulted in authentication bypass.

Administrative access then exposed additional functionality where XXE and SSRF could be investigated.

The SSRF provided access to an internal service, which returned encoded information.

After decoding the information, I obtained the credentials required for the second application.

The second application introduced another authorization flaw through scope manipulation, followed by a weak OTP mechanism.

This ultimately resulted in administrative access and completion of the challenge.

---

# Tools Used

### Web Application Testing

* Burp Suite
* Burp Suite Intruder
* Browser Developer Tools

### Reconnaissance

* Fuzzing tools
* Directory enumeration

### Analysis

* JWT.io
* Hexadecimal/encoding tools
* Python

---

# Skills Demonstrated

Through this challenge, I practiced:

* Web application reconnaissance
* Endpoint enumeration
* JWT analysis
* Authentication testing
* SQL Injection
* Authentication bypass
* XXE exploitation
* SSRF exploitation
* Internal service enumeration
* Encoding/decoding analysis
* OAuth authorization testing
* Privilege escalation
* OTP brute-force testing
* Attack-chain development
* Burp Suite-based traffic analysis
* Basic security automation with Python

---

# Key Takeaways

This challenge reinforced an important aspect of web application penetration testing:

> **A vulnerability does not always need to provide direct access to the final objective. It may provide information that enables the next step of the attack chain.**

The most valuable part of the challenge was therefore not simply identifying individual vulnerabilities, but understanding how each finding could be used to progress through the environment.

The overall methodology was:

```text
Observe
   ↓
Understand
   ↓
Form a hypothesis
   ↓
Test
   ↓
Analyze the result
   ↓
Extract useful information
   ↓
Update the attack path
   ↓
Repeat
```

This approach helped transform individual findings into a complete attack chain.

---

# Final Result

**WEB-RTA Challenge — Completed**

The challenge was successfully solved by chaining multiple web application vulnerabilities across two applications, ultimately obtaining administrative access and retrieving the final flag.

---

## Author

**Davi Rocha**

Cybersecurity | Web Application Security | Pentest | Red Team

---

> This write-up represents my personal learning process and documents the methodology I used during the challenge.
