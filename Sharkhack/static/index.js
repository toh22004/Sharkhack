document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#menu').onclick = () => {
        document.querySelector('#menu-view').style.display = 'block';
        document.querySelector('#workout-view').style.display = 'none';
        document.querySelector('#diet-view').style.display = 'none';
        document.querySelector('#profile-view').style.display = 'none';
        document.querySelector('#about-view').style.display = 'none';
    }

    document.querySelector('#workout').onclick = () => {
        document.querySelector('#menu-view').style.display = 'none';
        document.querySelector('#workout-view').style.display = 'block';
        document.querySelector('#diet-view').style.display = 'none';
        document.querySelector('#profile-view').style.display = 'none';
        document.querySelector('#about-view').style.display = 'none';
    }

    document.querySelector('#diet').onclick = () => {
        document.querySelector('#menu-view').style.display = 'none';
        document.querySelector('#workout-view').style.display = 'none';
        document.querySelector('#diet-view').style.display = 'block';
        document.querySelector('#profile-view').style.display = 'none';
        document.querySelector('#about-view').style.display = 'none';
    }

    document.querySelector('#profile').onclick = () => {
        document.querySelector('#menu-view').style.display = 'none';
        document.querySelector('#workout-view').style.display = 'none';
        document.querySelector('#diet-view').style.display = 'none';
        document.querySelector('#profile-view').style.display = 'block';
        document.querySelector('#about-view').style.display = 'none';
    }

    document.querySelector('#about').onclick = () => {
        document.querySelector('#menu-view').style.display = 'none';
        document.querySelector('#workout-view').style.display = 'none';
        document.querySelector('#diet-view').style.display = 'none';
        document.querySelector('#profile-view').style.display = 'none';
        document.querySelector('#about-view').style.display = 'block';
    }

    document.querySelector('form').onsubmit = (event) => {
        event.preventDefault();
        let message = document.getElementsByName('message')[0].value;
        let level = document.getElementsByName('level')[0].value;
        let mood = document.getElementsByName('mood')[0].value;
        let goal = document.getElementsByName('goal')[0].value;
        let performance = document.getElementsByName('performance')[0].value;
    
        fetch('/api/ai/assist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                level: level,
                mood: mood,
                goal: goal,
                performance: performance
            })
        })
        .then(response => response.json())
        .then(result => {
            console.log(result);
            document.querySelector('#content').innerHTML = result["response"];
          });
    }
});

