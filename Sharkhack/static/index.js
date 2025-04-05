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
        let goal = document.getElementsByName('goal')[0].value;
        let equipment = document.getElementsByName('equipment')[0].value;
        let mood = document.getElementsByName('mood')[0].value;
        let focus = document.getElementsByName('focus')[0].value;
        let duration = document.getElementsByName('duration')[0].value;
    
        fetch('/api/ai/generate-workout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                goal: goal,
                equipment: equipment,
                mood: mood,
                focus: focus,
                duration: duration
            })
        })
        .then(response => response.json())
        .then(result => {
            console.log(result["updated_plan"]["raw_response"]);
            document.querySelector('#content').innerHTML = result["updated_plan"]["raw_response"];
          });
    }
});

