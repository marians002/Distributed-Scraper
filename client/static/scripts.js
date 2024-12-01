function showLoginForm() {
  const loginForm = document.getElementById('loginForm');
  if (loginForm.style.display === 'none' || loginForm.style.display === '') {
    loginForm.style.display = 'block';
  } else {
    loginForm.style.display = 'none';
  }
}

function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const successMessage = document.getElementById('successMessage');
  const errorMessage = document.getElementById('errorMessage');

  // Simulate login verification
  if (email && password.length >= 6) {
    successMessage.style.display = 'block';
    errorMessage.style.display = 'none';

    // Simulate loading state
    const btn = event.target.querySelector('button');
    btn.disabled = true;
    btn.innerText = 'Logging in...';

    setTimeout(() => {
      btn.disabled = false;
      btn.innerText = 'Login';
      // Here you would typically redirect to a dashboard
    }, 2000);
  } else {
    successMessage.style.display = 'none';
    errorMessage.style.display = 'block';
  }
}

// Add smooth scrolling to all links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth'
    });
  });
});

// Add card hover animation
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('mouseover', function() {
    this.style.transform = 'translateY(-5px)';
  });

  card.addEventListener('mouseout', function() {
    this.style.transform = 'translateY(0)';
  });
});

function handleScrape(event) {
  event.preventDefault();
  const url = document.getElementById('url').value;
  const scrapeOption = document.getElementById('scrapeOption').value;

  fetch('/scrape', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      'url': url,
      'scrapeOption': scrapeOption
    })
  })
  .then(response => response.json())
  .then(data => {
    console.log(data);
    // Display the scraped data to the user
    alert(`Scraped Data: ${data.data}`);
  })
  .catch(error => {
    console.error('Error:', error);
  });
}