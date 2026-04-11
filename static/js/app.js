const API_URL = 'http://localhost:5000/api';
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function checkAuth() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
        currentUser = JSON.parse(user);
        showDashboard();
    }
}

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = e.target[0].value;
        const password = e.target[1].value;
        
        showLoading(e.target);
        
        try {
            const response = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                currentUser = data.user;
                closeModal('loginModal');
                showDashboard();
                showNotification('Login successful!', 'success');
            } else {
                showNotification(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showNotification('Login failed. Please try again.', 'error');
        } finally {
            hideLoading(e.target);
        }
    });
    
    // Register form
    document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = e.target[0].value;
        const email = e.target[1].value;
        const role = e.target[2].value;
        
        if (!role) {
            showNotification('Please select a role', 'error');
            return;
        }
        
        showLoading(e.target);
        
        try {
            const response = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, role })
            });
            
            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                currentUser = data.user;
                closeModal('registerModal');
                showDashboard();
                showNotification('Registration successful! Welcome to Submita!', 'success');
            } else {
                showNotification(data.error || 'Registration failed', 'error');
            }
        } catch (error) {
            console.error('Registration error:', error);
            showNotification('Registration failed. Please try again.', 'error');
        } finally {
            hideLoading(e.target);
        }
    });
    
    // Create assignment form
    document.getElementById('createAssignmentForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = e.target[0].value;
        const courseCode = e.target[1].value;
        const description = e.target[2].value;
        const deadline = e.target[3].value;
        
        if (!deadline) {
            showNotification('Please select a deadline', 'error');
            return;
        }
        
        showLoading(e.target);
        
        try {
            const response = await fetch(`${API_URL}/assignments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ title, course_code: courseCode, description, deadline })
            });
            
            if (response.ok) {
                closeModal('createAssignmentModal');
                loadLecturerDashboard();
                showNotification('Assignment created successfully!', 'success');
                e.target.reset();
            } else {
                showNotification('Failed to create assignment', 'error');
            }
        } catch (error) {
            console.error('Create assignment error:', error);
            showNotification('An error occurred', 'error');
        } finally {
            hideLoading(e.target);
        }
    });
}

function showDashboard() {
    // Hide landing sections
    const hero = document.querySelector('.hero');
    const features = document.querySelector('#features');
    const howItWorks = document.querySelector('#how-it-works');
    if (hero) hero.style.display = 'none';
    if (features) features.style.display = 'none';
    if (howItWorks) howItWorks.style.display = 'none';
    
    document.getElementById('dashboard').style.display = 'block';
    
    // Update UI based on role
    const roleBadge = document.getElementById('roleBadge');
    roleBadge.textContent = currentUser.role.toUpperCase();
    roleBadge.className = `role-badge ${currentUser.role}`;
    
    if (currentUser.role === 'lecturer') {
        document.getElementById('lecturerView').style.display = 'block';
        document.getElementById('studentView').style.display = 'none';
        loadLecturerDashboard();
    } else {
        document.getElementById('lecturerView').style.display = 'none';
        document.getElementById('studentView').style.display = 'block';
        loadStudentDashboard();
    }
    
    // Update navigation
    document.getElementById('navAuth').style.display = 'none';
    document.getElementById('navUser').style.display = 'flex';
    document.getElementById('userName').textContent = currentUser.name;
    document.getElementById('dashboardLink').style.display = 'inline';
}

async function loadLecturerDashboard() {
    try {
        const response = await fetch(`${API_URL}/assignments`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.assignments && data.assignments.length > 0) {
            // Load analytics for the first assignment
            const analyticsResponse = await fetch(`${API_URL}/analytics/${data.assignments[0].id}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const analytics = await analyticsResponse.json();
            
            document.getElementById('statsGrid').innerHTML = `
                <div class="stat-card">
                    <h3>${analytics.total_submissions}</h3>
                    <p>Total Submissions</p>
                </div>
                <div class="stat-card">
                    <h3>${analytics.average_grade.toFixed(1)}%</h3>
                    <p>Average Grade</p>
                </div>
                <div class="stat-card">
                    <h3>${analytics.plagiarism_alerts}</h3>
                    <p>Plagiarism Alerts</p>
                </div>
            `;
            
            // Load submissions
            document.getElementById('submissionsList').innerHTML = analytics.submissions.map(sub => `
                <div class="submission-item">
                    <div>
                        <strong>${sub.student_name}</strong>
                        <span style="color: var(--gray); margin-left: 1rem;">Grade: ${sub.grade || 'Pending'}</span>
                    </div>
                    <div>
                        <span style="background: ${sub.plagiarism > 30 ? 'var(--danger)' : 'var(--success)'}; 
                             color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;">
                            ${sub.plagiarism}% match
                        </span>
                    </div>
                </div>
            `).join('');
        } else {
            document.getElementById('statsGrid').innerHTML = '<p style="text-align: center; grid-column: 1/-1;">No assignments yet. Create your first assignment!</p>';
            document.getElementById('submissionsList').innerHTML = '<p>No submissions yet.</p>';
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Error loading dashboard', 'error');
    }
}

async function loadStudentDashboard() {
    showLoading(document.getElementById('assignmentsGrid'));
    
    try {
        const response = await fetch(`${API_URL}/assignments`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        const assignmentsGrid = document.getElementById('assignmentsGrid');
        
        if (data.assignments && data.assignments.length > 0) {
            assignmentsGrid.innerHTML = data.assignments.map(assignment => `
                <div class="assignment-card">
                    <h3>${assignment.title}</h3>
                    <p><strong>📚 Course:</strong> ${assignment.course_code}</p>
                    <p><strong>⏰ Deadline:</strong> ${new Date(assignment.deadline).toLocaleString()}</p>
                    <p><strong>📝 Description:</strong> ${assignment.description || 'No description provided'}</p>
                    <button class="btn btn-primary" onclick="showSubmitModal('${assignment.id}')">
                        📤 Submit Assignment
                    </button>
                </div>
            `).join('');
        } else {
            assignmentsGrid.innerHTML = '<p style="text-align: center; grid-column: 1/-1;">No active assignments at the moment.</p>';
        }
    } catch (error) {
        console.error('Error loading assignments:', error);
        showNotification('Error loading assignments', 'error');
    } finally {
        hideLoading(document.getElementById('assignmentsGrid'));
    }
}

async function showSubmitModal(assignmentId) {
    document.getElementById('submitModal').style.display = 'block';
    document.getElementById('submitForm').onsubmit = async (e) => {
        e.preventDefault();
        const file = e.target[0].files[0];
        const githubUrl = e.target[1].value;
        
        if (!file && !githubUrl) {
            showNotification('Please upload a file or provide a GitHub URL', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('assignment_id', assignmentId);
        if (file) formData.append('file', file);
        if (githubUrl) formData.append('github_url', githubUrl);
        
        showLoading(e.target);
        
        try {
            const response = await fetch(`${API_URL}/submit`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            
            const data = await response.json();
            if (response.ok) {
                closeModal('submitModal');
                showNotification(`Assignment submitted! Plagiarism score: ${data.plagiarism_score}%`, 'success');
                loadStudentDashboard();
                e.target.reset();
            } else {
                showNotification(data.error || 'Submission failed', 'error');
            }
        } catch (error) {
            console.error('Submission error:', error);
            showNotification('Submission failed. Please try again.', 'error');
        } finally {
            hideLoading(e.target);
        }
    };
}

function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
}

function showRegisterModal() {
    document.getElementById('registerModal').style.display = 'block';
}

function showCreateAssignmentModal() {
    document.getElementById('createAssignmentModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function logout() {
    localStorage.clear();
    currentUser = null;
    location.reload();
}

function scrollToFeatures() {
    document.getElementById('features').scrollIntoView({ behavior: 'smooth' });
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '300px';
    notification.style.animation = 'slideIn 0.3s ease-out';
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function showLoading(element) {
    if (element && element.querySelector) {
        const btn = element.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Processing...';
        }
    }
}

function hideLoading(element) {
    if (element && element.querySelector) {
        const btn = element.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = false;
            btn.textContent = btn.getAttribute('data-original-text') || 
                            (btn.textContent === 'Processing...' ? 'Submit' : btn.textContent);
        }
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);