const addTaskButton = document.getElementById("add-task");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");

// Create a responsibility row safely
function createTaskRow(task) {
    const row = document.createElement("div");
    row.className = "task-row";

    const icon = document.createElement("span");
    icon.className = "task-icon";
    icon.textContent = "☷";

    const info = document.createElement("div");
    info.className = "task-info";

    const name = document.createElement("strong");
    name.textContent = task.title;

    const description = document.createElement("small");

    const taskDescription = task.description || "No description";
    const assignedPerson = task.assigned_to || "Unassigned";

    description.textContent =
        taskDescription + " · Assigned to: " + assignedPerson;

    info.append(name, description);

    const priority = document.createElement("span");
    priority.className = "priority medium";
    priority.textContent = task.status || "Pending";

    row.append(icon, info, priority);

    // Edit Responsibility button
    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "responsibility-edit-btn";
    editButton.textContent = "Edit";

    editButton.addEventListener("click", async () => {
        const newTitle = prompt("Edit title:", task.title);
        if (newTitle === null) return;

        const newDescription = prompt(
            "Edit description:",
            task.description || ""
        );
        if (newDescription === null) return;

        const newAssignedTo = prompt(
            "Edit assigned person:",
            task.assigned_to || ""
        );
        if (newAssignedTo === null) return;

        const allowedStatuses = ["Pending", "In Progress", "Completed"];

        const newStatus = prompt(
            "Enter status: Pending, In Progress, or Completed",
            allowedStatuses.includes(task.status)
                ? task.status
                : "Pending"
        );

        if (newStatus === null) return;

        if (!newTitle.trim()) {
            alert("Title is required.");
            return;
        }

        if (!allowedStatuses.includes(newStatus.trim())) {
            alert("Please enter Pending, In Progress, or Completed.");
            return;
        }

        try {
            const updateResponse = await fetch(
                `/api/responsibilities/${task.id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        title: newTitle.trim(),
                        description: newDescription.trim(),
                        assigned_to: newAssignedTo.trim(),
                        status: newStatus.trim()
                    })
                }
            );

            const result = await updateResponse.json();

            if (!updateResponse.ok) {
                throw new Error(
                    result.error || "Could not update responsibility"
                );
            }

            alert("Responsibility updated successfully!");
            await loadResponsibilities();

        } catch (error) {
            alert(error.message);
        }
    });

    row.appendChild(editButton);

    if (task.qr_token) {
        const qrImage = document.createElement("img");
        qrImage.className = "task-qr";
        qrImage.alt = "QR code for " + task.title;
        qrImage.src =
            `/responsibility/${encodeURIComponent(task.qr_token)}/qr.png`;

        const qrLink = document.createElement("a");
        qrLink.href =
            `/responsibility/${encodeURIComponent(task.qr_token)}`;
        qrLink.textContent = "Open details";
        qrLink.target = "_blank";
        qrLink.rel = "noopener noreferrer";

        const qrContainer = document.createElement("div");
        qrContainer.className = "qr-container";
        qrContainer.append(qrImage, qrLink);
        row.appendChild(qrContainer);
    }

    // Remove Responsibility button
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "responsibility-remove-btn";
    removeButton.textContent = "Remove";

    removeButton.addEventListener("click", async () => {
        const confirmed = confirm(
            `Remove responsibility "${task.title}"? Its QR link will stop working.`
        );

        if (!confirmed) return;

        try {
            const deleteResponse = await fetch(
                `/api/responsibilities/${task.id}`,
                { method: "DELETE" }
            );

            const result = await deleteResponse.json();

            if (!deleteResponse.ok) {
                throw new Error(
                    result.error || "Could not remove responsibility"
                );
            }

            alert("Responsibility removed successfully!");
            await loadResponsibilities();
        } catch (error) {
            alert(error.message);
        }
    });

    row.appendChild(removeButton);
    taskList.appendChild(row);
}

// GET: Load responsibilities from Flask/SQLite
async function loadResponsibilities() {
    try {
        const response = await fetch("/api/responsibilities");

        if (!response.ok) {
            throw new Error("Failed to load responsibilities");
        }

        const responsibilities = await response.json();

        // Remove hardcoded sample rows
        taskList.replaceChildren();

        responsibilities.forEach(createTaskRow);

        taskCount.textContent = responsibilities.length;

    } catch (error) {
        console.error("Load error:", error);
        alert("Could not load responsibilities from backend.");
    }
}

// POST: Add responsibility to Flask/SQLite
addTaskButton.addEventListener("click", async () => {
    const title = prompt("Enter a responsibility:");

    if (!title || !title.trim()) {
        return;
    }

    const description = prompt("Enter task description (optional):") || "";
    const assignedTo = prompt("Who is responsible for this task?") || "";

    try {
        const response = await fetch("/api/responsibilities", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title.trim(),
                description: description.trim(),
                assigned_to: assignedTo.trim()
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Save failed");
        }

        await loadResponsibilities();

    } catch (error) {
        console.error("Save error:", error);
        alert("Could not save responsibility. Check Flask terminal.");
    }
});

// Load database entries when page opens
loadResponsibilities();
const contactList = document.getElementById("contact-list");
const addContactButton = document.getElementById("add-contact");
const contactCount = document.getElementById("contact-count");

async function loadContacts() {
    try {
        const response = await fetch("/api/contacts");

        if (!response.ok) {
            throw new Error("Failed to load contacts");
        }

        const contacts = await response.json();

        contactList.replaceChildren();

        contacts.forEach((contact, index) => {
            const row = document.createElement("div");
            row.className = "contact-row";

            const avatar = document.createElement("div");
            avatar.className =
                "contact-avatar" + (index % 2 ? " purple" : "");
            avatar.textContent = contact.name.charAt(0).toUpperCase();

            const info = document.createElement("div");
            info.className = "task-info";

            const name = document.createElement("strong");
            name.textContent = contact.name;

            const phone = document.createElement("small");
            phone.textContent = contact.phone;

            info.append(name, phone);

            const actions = document.createElement("div");
            actions.className = "contact-actions";

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.textContent = "Edit";
            editButton.className = "contact-edit-btn";

            editButton.addEventListener("click", async () => {
                const newName = prompt("Enter contact name:", contact.name);
                if (newName === null) return;

                const newPhone = prompt("Enter contact phone:", contact.phone);
                if (newPhone === null) return;

                if (!newName.trim() || !newPhone.trim()) {
                    alert("Name and phone are required.");
                    return;
                }

                try {
                    const result = await fetch(`/api/contacts/${contact.id}`, {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            name: newName.trim(),
                            phone: newPhone.trim()
                        })
                    });

                    const data = await result.json();

                    if (!result.ok) {
                        throw new Error(data.error || "Could not update contact");
                    }

                    alert("Contact updated successfully!");
                    await loadContacts();

                    if (typeof loadEmergencyContacts === "function") {
                        await loadEmergencyContacts();
                    }
                } catch (error) {
                    alert(error.message);
                }
            });

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.textContent = "Remove";
            removeButton.className = "contact-remove-btn";

            removeButton.addEventListener("click", async () => {
                if (!confirm(`Remove ${contact.name} from trusted contacts?`)) {
                    return;
                }

                try {
                    const result = await fetch(`/api/contacts/${contact.id}`, {
                        method: "DELETE"
                    });

                    const data = await result.json();

                    if (!result.ok) {
                        throw new Error(data.error || "Could not remove contact");
                    }

                    alert("Contact removed successfully!");
                    await loadContacts();

                    if (typeof loadEmergencyContacts === "function") {
                        await loadEmergencyContacts();
                    }
                } catch (error) {
                    alert(error.message);
                }
            });

            actions.append(editButton, removeButton);
            row.append(avatar, info, actions);
            contactList.appendChild(row);
        });

        contactCount.textContent = contacts.length;

    } catch (error) {
        console.error("Contact load error:", error);
    }
}

addContactButton.addEventListener("click", async () => {
    const name = prompt("Enter contact name:");
    if (!name || !name.trim()) return;

    const phone = prompt("Enter contact phone number:");
    if (!phone || !phone.trim()) return;

    try {
        const response = await fetch("/api/contacts", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name.trim(),
                phone: phone.trim()
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Contact save failed");
        }

        await loadContacts();

    } catch (error) {
        console.error("Contact save error:", error);
        alert("Could not save contact. Check the Flask terminal.");
    }
});

loadContacts();
const emergencyContact = document.getElementById("emergency-contact");
const emergencyNotes = document.getElementById("emergency-notes");
const prepareEmergencyButton =
    document.getElementById("prepare-emergency");
const emergencyResult = document.getElementById("emergency-result");

async function loadEmergencyContacts() {
    try {
        const response = await fetch("/api/contacts");

        if (!response.ok) {
            throw new Error("Could not load trusted contacts");
        }

        const contacts = await response.json();

        emergencyContact.replaceChildren();

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = contacts.length
            ? "Select a trusted contact"
            : "No trusted contacts saved";

        emergencyContact.appendChild(placeholder);

        contacts.forEach(contact => {
            const option = document.createElement("option");
            option.value = String(contact.id);
            option.textContent = contact.name;
            emergencyContact.appendChild(option);
        });

    } catch (error) {
        console.error("Emergency contacts error:", error);
        emergencyContact.replaceChildren();

        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Unable to load contacts";
        emergencyContact.appendChild(option);
    }
}
const emergencyPlanList = document.getElementById("emergency-plan-list");

async function loadEmergencyPlans() {
    try {
        const response = await fetch("/api/emergency-plans");

        if (!response.ok) {
            throw new Error("Could not load saved emergency plans");
        }

        const plans = await response.json();
        emergencyPlanList.replaceChildren();

        if (plans.length === 0) {
            const emptyMessage = document.createElement("p");
            emptyMessage.className = "demo-note";
            emptyMessage.textContent = "No saved emergency plans yet.";
            emergencyPlanList.appendChild(emptyMessage);
            return;
        }

        plans.forEach(plan => {
            const card = document.createElement("article");
            card.className = "saved-plan-card";

            const heading = document.createElement("h4");
            heading.textContent = "Plan #" + plan.id;

            const contact = document.createElement("p");
            contact.textContent = "Trusted contact: " + plan.contact_name;

            const notes = document.createElement("p");
            notes.textContent = "Notes: " + (plan.situation_notes || "None");

            const date = document.createElement("small");
            date.textContent = "Saved: " + (plan.created_at || "Unknown");

            const actions = document.createElement("div");
            actions.className = "plan-actions";

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "plan-edit-btn";
            editButton.textContent = "Edit";

            editButton.addEventListener("click", async () => {
                const newNotes = prompt(
                    "Edit situation notes:",
                    plan.situation_notes || ""
                );

                if (newNotes === null) return;

                const contactsResponse = await fetch("/api/contacts");

                if (!contactsResponse.ok) {
                    alert("Could not load trusted contacts.");
                    return;
                }

                const contacts = await contactsResponse.json();

                if (contacts.length === 0) {
                    alert("Add a trusted contact before editing this plan.");
                    return;
                }

                const contactOptions = contacts
                    .map(c => `${c.id}: ${c.name}`)
                    .join("\n");

                const selectedId = prompt(
                    "Enter the ID of the trusted contact:\n" + contactOptions,
                    String(plan.contact_id)
                );

                if (selectedId === null) return;

                const contactId = Number(selectedId);

                if (!Number.isInteger(contactId) ||
                    !contacts.some(c => c.id === contactId)) {
                    alert("Please enter a valid contact ID.");
                    return;
                }

                try {
                    const updateResponse = await fetch(
                        `/api/emergency-plans/${plan.id}`,
                        {
                            method: "PUT",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                contact_id: contactId,
                                situation_notes: newNotes.trim()
                            })
                        }
                    );

                    const result = await updateResponse.json();

                    if (!updateResponse.ok) {
                        throw new Error(
                            result.error || "Could not update plan"
                        );
                    }

                    alert("Emergency plan updated successfully!");
                    await loadEmergencyPlans();
                } catch (error) {
                    alert(error.message);
                }
            });

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "plan-remove-btn";
            removeButton.textContent = "Remove";

            removeButton.addEventListener("click", async () => {
                const confirmed = confirm(
                    `Remove Emergency Plan #${plan.id}?`
                );

                if (!confirmed) return;

                try {
                    const deleteResponse = await fetch(
                        `/api/emergency-plans/${plan.id}`,
                        { method: "DELETE" }
                    );

                    const result = await deleteResponse.json();

                    if (!deleteResponse.ok) {
                        throw new Error(
                            result.error || "Could not remove plan"
                        );
                    }

                    alert("Emergency plan removed successfully!");
                    await loadEmergencyPlans();
                } catch (error) {
                    alert(error.message);
                }
            });

            actions.append(editButton, removeButton);
            card.append(heading, contact, notes, date, actions);
            emergencyPlanList.appendChild(card);
        });
    } catch (error) {
        console.error("Saved plans loading error:", error);
        emergencyPlanList.textContent = "Could not load saved plans.";
    }
}

loadEmergencyPlans();

prepareEmergencyButton.addEventListener("click", async () => {
    const contactId = emergencyContact.value;
    const notes = emergencyNotes.value.trim();

    if (!contactId) {
        emergencyResult.textContent =
            "Please select a saved trusted contact first.";
        return;
    }

    prepareEmergencyButton.disabled = true;
    emergencyResult.textContent = "Saving emergency plan...";

    try {
        const response = await fetch("/api/emergency-plans", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                contact_id: Number(contactId),
                situation_notes: notes
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.error || "Could not save emergency plan."
            );
        }

        const savedPlan = result.plan;

        emergencyResult.textContent =
            "Emergency plan saved successfully. " +
            "Saved at: " + savedPlan.created_at +
            ". No contact has been notified.";

    } catch (error) {
        console.error("Emergency plan save error:", error);
        emergencyResult.textContent =
            "Could not save the plan: " + error.message;
    } finally {
        prepareEmergencyButton.disabled = false;
    }
});

loadEmergencyContacts();

async function loadNotificationLogs() {
    const list = document.getElementById("notification-list");
    const refreshButton = document.getElementById("refresh-notifications");

    if (!list || !refreshButton) return;

    refreshButton.disabled = true;
    list.replaceChildren();

    const loading = document.createElement("p");
    loading.textContent = "Loading notification history...";
    list.appendChild(loading);

    try {
        const response = await fetch("/api/notification-logs");

        if (!response.ok) {
            throw new Error("Could not load notification history");
        }

        const data = await response.json();
        list.replaceChildren();

        const logs = Array.isArray(data.logs) ? data.logs : [];

        if (logs.length === 0) {
            const empty = document.createElement("p");
            empty.textContent = "No demo notifications recorded yet.";
            list.appendChild(empty);
            return;
        }

        logs.forEach((log) => {
            const card = document.createElement("article");
            card.className = "notification-card";

            const heading = document.createElement("h3");
            heading.textContent = log.recipient_type || "Demo recipient";

            const status = document.createElement("span");
            status.className = "demo-status";
            status.textContent =
                log.delivery_status || "DEMO_ONLY_NOT_SENT";

            const details = document.createElement("p");
            details.textContent =
                log.message || "Demo record only; nothing was sent.";

            const timestamp = document.createElement("small");
            timestamp.textContent =
                "Recorded: " + (log.created_at || "Time unavailable");

            const alertId = document.createElement("small");
            alertId.textContent = "Alert ID: " + log.alert_id;

            card.append(heading, status, details, timestamp, alertId);
            list.appendChild(card);
        });
    } catch (error) {
        console.error("Notification history error:", error);

        list.replaceChildren();
        const errorMessage = document.createElement("p");
        errorMessage.textContent =
            "Could not load notification history. Check the Flask server.";
        list.appendChild(errorMessage);
    } finally {
        refreshButton.disabled = false;
    }
}

const refreshNotificationsButton =
    document.getElementById("refresh-notifications");

if (refreshNotificationsButton) {
    refreshNotificationsButton.addEventListener(
        "click",
        loadNotificationLogs
    );
}

loadNotificationLogs();