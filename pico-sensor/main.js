/*
Copyright 2024 Hex-Software Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

async function fetchWithRetry(url, options = {}, retries = 3, backoff = 3000) {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response; // or response.json() if you want to parse the JSON body
    } catch (error) {
        if (retries > 0) {
            console.log(`Retrying... attempts left: ${retries}`);
            await new Promise((resolve) => setTimeout(resolve, backoff)); // wait before retrying
            return fetchWithRetry(url, options, retries - 1, backoff * 2); // retry with exponential backoff
        } else {
            throw new Error(`Max retries reached. Error: ${error.message}`);
        }
    }
}

function updateGivenName(name) {
    console.log("updateGivenName() called");
    const givenNameElement = document.getElementById('given-name');
    givenNameElement.innerText = name;
};

function updateUUID(uuid) {
    const uuidElement = document.getElementById('uuid');
    uuidElement.innerText = uuid;
}

window.onload = function() {
    fetchWithRetry('/device_meta', { method: 'GET' })
        .then(response => response.json())
        .then(responseData => {
            console.log("response data:", responseData);
            updateGivenName(responseData.name);
            updateUUID(responseData.uuid);
        })
};

function toggleLed() {
    console.log("toggle led");
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/led", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            try {
                var response = JSON.parse(xhr.responseText);
                console.log(response);
            } catch (e) {
                console.log("Error parsing JSON response", e);
            }
        }
    }
    xhr.send();
}

function update_software() {
    console.log("update software");
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/update_software", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            try {
                var response = JSON.parse(xhr.responseText);
                console.log(response);
            } catch (e) {
                console.log("Error parsing JSON response", e);
            }
        }
    }
    xhr.send();
}

function check_updates_available() {
    console.log("check updates available");
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/updates_available", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            try {
                var response = JSON.parse(xhr.responseText);
                console.log(response);
                updates_available = response.updates_available;
                if (updates_available) {
                    document.getElementById('updates_available').innerHTML = "Updates available";
                    document.getElementById('update_button').onclick = update_software;
                    document.getElementById('update_button').innerHTML = "Update";
                } else {
                    document.getElementById('updates_available').innerHTML = "No updates available";
                    document.getElementById('update_button').onclick = check_updates_available;
                    document.getElementById('update_button').innerHTML = "Check for available updates";}
            } catch (e) {
                console.log("Error parsing JSON response", e);
            }
        }
    }
    xhr.send();
}
