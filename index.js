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
                json_file = json_file.slice(7);
                json_file = json_file.slice(0, -3);
                const json_real_file = JSON.parse(json_file);
                console.log(json_real_file);
                console.log(json_real_file["plan_name"]);

                let message = document.querySelector('#content');
                message.innerHTML = "";
                message.innerHTML += `<h2 style="width: 70%;">${json_real_file["plan_name"]}</h2>`;

                message.innerHTML += `<br><br>`;

                message.innerHTML += `<h3 style="width: 45%;">Warm-Up:</h3>`;
                for (let i = 0; i < json_real_file["warm_up"].length; i++) {
                    message.innerHTML += `<p>${json_real_file["warm_up"][i]["exercise"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["warm_up"][i]["reps"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["warm_up"][i]["form_tip"]}</p>`;
                    message.innerHTML += `+++++`;
                }

                message.innerHTML += `<br><br>`;

                message.innerHTML += `<h3 style="width: 45%;">Main Workout:</h3>`;
                for (let i = 0; i < json_real_file["main_workout"].length; i++) {
                    message.innerHTML += `<p>${json_real_file["main_workout"][i]["exercise"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["main_workout"][i]["reps"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["main_workout"][i]["form_tip"]}</p>`;
                    message.innerHTML += `+++++`;
                }

                message.innerHTML += `<br><br>`;

                message.innerHTML += `<h3 style="width: 45%;">Cool Down:</h3>`;
                for (let i = 0; i < json_real_file["cool_down"].length; i++) {
                    message.innerHTML += `<p>${json_real_file["cool_down"][i]["exercise"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["cool_down"][i]["reps"]}</p>`;
                    message.innerHTML += `<p>${json_real_file["cool_down"][i]["form_tip"]}</p>`;
                    message.innerHTML += `+++++`;
                }

                message.innerHTML += `<br><br>`;
                
                
                // Optionally update the UI
                message.style.display = 'block';
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
                console.log(result["explanation"]);
                document.querySelector('#content').style.display = 'none';
                workoutForm2.style.display = 'none';
                const content2 = document.querySelector('#content2');
                if (content2) {
                    content2.innerHTML = result["explanation"];
                }
            });
        }
    }

    const dietForm = document.querySelector('#diet-form');
    if (dietForm) {
        dietForm.onsubmit = (event) => {
            event.preventDefault();
            let meal_type = document.getElementsByName('meal_type')[0].value;

            fetch('/api/ai/generate-meal-suggestion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    meal_type: meal_type
                })
            })
            .then(response => response.json())
            .then(result => {
                console.log(result["suggestion"]);
                document.querySelector('#diet-form').style.display = 'none';
                document.querySelector('#intro-diet').style.display = 'block';
                document.querySelector('#content11').innerHTML = result["suggestion"];
            });
        }
    }
})