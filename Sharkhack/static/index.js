document.addEventListener('DOMContentLoaded', function() {
    /*
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
        */
    const workoutForm = document.querySelector('#workout-form');
    if (workoutForm) {
        workoutForm.onsubmit = (event) => {
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
                let json_file = result["updated_plan"]["raw_response"];
                console.log(json_file);
                // Optionally update the UI
                workoutForm.style.display = 'none';
                const workoutForm2 = document.querySelector('#workout-form2');
                if (workoutForm2) {
                    workoutForm2.style.display = 'block';
                }
            });
        }
    }
    
    const workoutForm2 = document.querySelector('#workout-form2');
    if (workoutForm2) {
        workoutForm2.onsubmit = (event) => {
            event.preventDefault();
            let completed = document.getElementsByName('completed')[0].value;
            let difficulty_rating = document.getElementsByName('difficulty_rating')[0].value;
            let notes = document.getElementsByName('notes')[0].value;
            fetch('/api/ai/update-workout-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    completed: completed,
                    difficulty_rating: difficulty_rating,
                    notes: notes
                })
            })
            .then(response => response.json())
            .then(result => {
                console.log(result);
                workoutForm2.style.display = 'none';
                const content2 = document.querySelector('#content2');
                if (content2) {
                    content2.innerHTML = result;
                }
            });
        }
    }
})