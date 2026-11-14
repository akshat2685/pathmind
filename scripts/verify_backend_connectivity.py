import urllib.request
import json
import sys

base_url = 'http://127.0.0.1:8000'

def test_endpoint(name, path, method='GET', data=None, headers=None):
    url = base_url + path
    h = headers or {}
    body = None
    if data:
        body = json.dumps(data).encode('utf-8')
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            print(f'[PASS] {name}: HTTP {response.status}')
            return res
    except Exception as e:
        print(f'[FAIL] {name} failed: {e}')
        raise

def main():
    print('=============================================')
    print('  TESTING LIVE BACKEND CONNECTIVITY & STORE  ')
    print('=============================================')
    
    # 1. API Health
    root = test_endpoint('API Health Root', '/')
    print(f'  Service Status: {root.get("service")} - {root.get("status")}')

    # 2. Users Registry Before
    users_before = test_endpoint('List Users Before', '/api/college/users')
    print(f'  Existing registered users in DB: {len(users_before)}')

    # 3. Register New Scholar Profile
    test_uid = 'priya-nair-cse'
    prof = test_endpoint(
        'Register New Scholar Profile',
        '/api/college/profile',
        method='POST',
        data={'name': 'Priya Nair', 'email': 'priya@college.edu', 'supported_path': 'COMPUTER_SCIENCE_ENGINEER'},
        headers={'X-Person-ID': test_uid}
    )
    print(f'  Registered: {prof.get("name")} ({prof.get("uid")})')

    # 4. Search Universities
    univs = test_endpoint('Search Universities', '/api/college/universities?query=anna')
    print(f'  Found {len(univs)} universities matching query "anna"')

    # 5. Resolve Curriculum for Branch & Semester
    curr = test_endpoint(
        'Resolve Curriculum',
        '/api/college/curriculum?university_id=univ_anna&branch=COMPUTER_SCIENCE_ENGINEER&semester=5'
    )
    subjects = curr.get("subjects", [])
    print(f'  Curriculum: {curr.get("program_name")} with {len(subjects)} subjects')

    # 6. Save Academic Context
    acad = test_endpoint(
        'Save Academic Context',
        '/api/college/academic-context',
        method='POST',
        data={
            'university_id': 'univ_anna',
            'branch': 'COMPUTER_SCIENCE_ENGINEER',
            'semester': 5,
            'subjects': ['CS8591', 'CS8592'],
            'available_hours_per_week': 18,
            'learning_style_preferences': ['visual', 'practice-heavy']
        },
        headers={'X-Person-ID': test_uid}
    )
    print(f'  Academic context saved: Sem {acad.get("semester")} at {acad.get("university_id")}')

    # 7. Generate Ordered Study Plan
    plan = test_endpoint(
        'Generate Ordered Study Plan',
        '/api/college/plans/generate',
        method='POST',
        data={'goal_id': 'goal_semester_prep', 'target_subject_code_or_id': 'CS8591'},
        headers={'X-Person-ID': test_uid}
    )
    phases = plan.get("phases", [])
    print(f'  Plan generated: {len(phases)} phases.')
    if phases:
        p1 = phases[0]
        print(f'  Phase 1: "{p1.get("title")}" with {len(p1.get("activities", []))} ordered activities')
        for act in p1.get("activities", [])[:3]:
            print(f'    - [{act.get("activity_type")}] {act.get("title")} (Required: {act.get("required")})')

    # 8. Retrieve Authentic PYQs
    pyqs = test_endpoint('Retrieve Verified PYQs', '/api/college/pyqs?subject_id=CS8591')
    print(f'  PYQ Status: {pyqs.get("status")}, total questions: {len(pyqs.get("questions", []))}')

    # 9. Accountability Schedule
    sched = test_endpoint(
        'Accountability Today Schedule',
        '/api/college/accountability/today',
        headers={'X-Person-ID': test_uid}
    )
    print(f'  Exam days remaining: {sched.get("exam_days_remaining")}, commitments today: {len(sched.get("commitments", []))}')

    # 10. Silent Memory Vault (Backend-only personal context)
    mem = test_endpoint(
        'Silent Personal Memory Vault',
        '/api/college/memory',
        headers={'X-Person-ID': test_uid}
    )
    print(f'  Personal Memory Vault (Backend only):')
    print(f'    Short-term working memories: {len(mem.get("short_term", []))}')
    print(f'    Long-term longitudinal memories: {len(mem.get("long_term", []))}')
    print(f'    Learning signals / misconceptions: {len(mem.get("learning_signals", []))}')

    # 11. List All Users to ensure new user is listed
    users_after = test_endpoint('List All Users After Registration', '/api/college/users')
    print(f'  Registered users in DB: {len(users_after)}')
    for u in users_after:
        print(f'    -> Scholar: {u.get("name")} ({u.get("uid")}) | Univ: {u.get("primary_university_id")} | Branch: {u.get("primary_branch")} | Sem: {u.get("current_semester")}')

    print('=============================================')
    print('  ALL LIVE BACKEND SERVICES 100% OPERATIONAL ')
    print('=============================================')

if __name__ == '__main__':
    main()
