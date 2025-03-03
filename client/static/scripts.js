let linksList = [];
let currentLinkIndex = 0;

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

// Add copy button
document.getElementById("copyButton").addEventListener("click", function() {
  var textarea = document.getElementById("myTextarea");
  textarea.select();
  document.execCommand("copy");
  alert("Text copied to clipboard!");
});

async function getPowChallenge() {
  const response = await fetch('/get-pow-challenge');
  const data = await response.json();
  return data.challenge;
}

function solvePowChallenge(challenge, difficulty) {
  let nonce = 0;

  while (true) {
    const hash = CryptoJS.SHA256(challenge + nonce).toString();
    if (hash.startsWith('0'.repeat(difficulty))) {
      console.log(hash)
      return nonce;
    }
    nonce++;
  }
}

function showLoadingSpinner() {
  const spinner = document.getElementById('loadingSpinner');
  spinner.style.display = 'block';
}

function hideLoadingSpinner() {
  const spinner = document.getElementById('loadingSpinner');
  spinner.style.display = 'none';
}

async function performScrape(url, scrapeOption, depth) {
  showLoadingSpinner(); // Show spinner before starting the challenge

  const challenge = await getPowChallenge();
  const difficulty = 4;
  const nonce = solvePowChallenge(challenge, difficulty);

  const response = await fetch('/scrape', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      'url': url,
      'scrapeOption': scrapeOption,
      'depth': depth,
      'challenge': challenge,
      'nonce': nonce
    })
  });

  hideLoadingSpinner(); // Hide spinner after the challenge is solved
  return response.text();
}

async function handleScrape(event) {
  event.preventDefault();

  const url = document.getElementById('url').value;
  const scrapeOption = document.getElementById('scrapeOption').value;
  const depth = document.getElementById('depth').value;

  try {
    const data = await performScrape(url, scrapeOption, depth);
    const scrapedDataTextarea = document.getElementById('scrapedData');
    const copyBut = document.getElementById('copy-btn');
    scrapedDataTextarea.style.display = 'block';
    copyBut.style.display = 'flex';
    scrapedDataTextarea.value = data;
  } catch (error) {
    console.error('Error:', error);
  }
}

function handleFileScrape(event) {
  event.preventDefault(); // Prevent the form from submitting

  const fileInput = document.getElementById('file');
  const file = fileInput.files[0];

  if (!file) {
    alert('Please select a file.');
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const content = e.target.result;
    linksList = content.split('\n').filter(link => link.trim() !== '');

    console.log("Number of links: " + linksList.length);
    console.log("Links: ");
    for (let i = 0; i < linksList.length; i++) {
      console.log(linksList[i]);
    }

    currentLinkIndex = 0;
  };
  reader.readAsText(file);
}

async function scrapeNextLink() {
  if (currentLinkIndex >= linksList.length) {
    alert('No more links to scrape.');
    return;
  }

  const url = linksList[currentLinkIndex];
  const scrapeOption = document.getElementById('scrapeOption').value;
  const depth = document.getElementById('depth').value; 

  try {
    const data = await performScrape(url, scrapeOption, depth);
    const scrapedDataTextarea = document.getElementById('scrapedData');
    const copyBut = document.getElementById('copy-btn');
    scrapedDataTextarea.style.display = 'block';
    copyBut.style.display = 'flex';
    scrapedDataTextarea.value = data;
  } catch (error) {
    console.error('Error:', error);
  }

  currentLinkIndex++;
}

// Function to copy text to clipboard
function copyToClipboard() {
  const textarea = document.getElementById('scrapedData');
  textarea.select();
  document.execCommand('copy');

  // Show the "Copied!" message
  const copyMessage = document.getElementById('copy-message');
  copyMessage.style.display = 'inline';

  // Hide the message after 3 seconds
  setTimeout(() => {
    copyMessage.style.display = 'none';
  }, 3000);
}

document.getElementById('fileUploadForm').addEventListener('submit', handleFileScrape);
document.getElementById('scrapeNextLinkBtn').addEventListener('click', scrapeNextLink);