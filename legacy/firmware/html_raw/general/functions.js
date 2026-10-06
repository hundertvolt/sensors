function updateCurrentValues(currentValues) {
    fetch(currentValues.script_cfg.addr)
        .then(response => response.json())
        .then(data => {
            if (currentValues.script_cfg.multi_val) {
                for (const sensor in data) {
                    for (const property in data[sensor]) {
                        const key = sensor + '_' + property;
                        if (currentValues[key]) {
                            currentValues[key].textContent = data[sensor][property];
                        }
                    }
                }
            } else {
                for (const setting in data) {
                    if (currentValues[setting]) {
                        currentValues[setting].textContent = data[setting];
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

function putSensorCfg(inputFields, currentValues) {
    const requestData = { cmd: inputFields.script_cfg.cmd };
    for (const field in inputFields) {
        if (field !== 'script_cfg') {
            if (inputFields[field] instanceof HTMLInputElement || inputFields[field] instanceof HTMLTextAreaElement || inputFields[field] instanceof HTMLSelectElement) {
                requestData[field] = inputFields[field].value;
                inputFields[field].value = "";
            } else {
                requestData[field] = inputFields[field].textContent;
                inputFields[field].textContent = "";
            }
        }
    }
    const requestOptions = {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
    };
    fetch(inputFields.script_cfg.addr, requestOptions)
        .then(response => response.json())
        .then(data => {
            if (data.result) {
                for (const field in inputFields) {
                    if ((field !== 'script_cfg') && data.result[field]) {
                        const color = getColorForValue(data.result[field]);
                        var parent = inputFields[field].parentNode;
                        while ((parent.tagName !== 'DIV') || !(parent.classList.contains('card'))) {  // iterate through until the closest DIV card, is reached
                            parent = parent.parentNode;
                        }
                        parent.style.backgroundColor = color;
                    }
                }
            }
            inputFields.script_cfg.result.textContent = "Result: " + data.descr;
        })
        .catch(error => {
            console.error('Error processing response:', error);
        });
    if (currentValues !== null) {
        setTimeout(updateCurrentValues, 2000, currentValues);
    }
}

function getColorForCode(value) {
    switch (value) {
        case 0:
            return "#FFFFFF"; // OK: White
        case 8:
            return "#DDBFD8"; // LED busy: Light lavender
        case 10:
            return "#DDBFD8"; // Unknown sys command: Light lavender
        default:
            return "#FFFFFF"; // Default to white
    }
}

function getColorForValue(value) {
    switch (value) {
        case "Valid":
            return "#98FB98"; // Light green
        case "Unchanged":
            return "#DDDDDD"; // Light grey
        case "Invalid":
            return "#FF7F7F"; // Light red
        case "Failed":
            return "#DDBFD8"; // Light lavender
        default:
            return "#FFFFFF"; // Default to white
    }
}

function toggleButtonSwitch(inputFields, key, startValueBool) {
    if ((inputFields[key].textContent !== "Off") && (inputFields[key].textContent !== "On")) { // uninitialized
        inputFields[key].style.fontWeight = "bold";
        if (startValueBool) {
            inputFields[key].textContent = "On";
        } else {
            inputFields[key].textContent = "Off";
        }
    } else {  // initialized
        if (inputFields[key].textContent !== "Off") {
            inputFields[key].textContent = "Off";
        } else {
            inputFields[key].textContent = "On";
        }
    }
}
