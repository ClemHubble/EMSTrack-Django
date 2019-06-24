/**
 * Patient base class
 */
export class Patients {
    
    constructor(patients = [], label = 'new', placeholder = '#patients') {
        this.patients= patients;
        this.label = label;
        this.placeholder = $(placeholder);
    }

    static patientForm(label, symbol, patient) {

        return (
            '<div class="form-row" id="patient-' + label + '-form">' +
            '  <div class="col-md-7 pr-0">' +
            '    <input id="patient-' + label + '-id" ' +
            '           type="hidden" ' +
            '           value="' + patient.id + '">' +
            '    <input id="patient-' + label + '-name" ' +
            '           type="text" ' +
            '           class="form-control" ' +
            '           value="' + patient.name + '" ' +
            '           placeholder="' + translation_table['Name'] + '">' +
            '  </div>' +
            '  <div class="col-md-3 px-0">' +
            '    <input id="patient-' + label + '-age" ' +
            '           type="number" min="0" ' +
            '           class="form-control" ' +
            '           value="' + patient.age + '" ' +
            '           placeholder="' + translation_table['Age'] + '">' +
            '  </div>' +
            '  <div class="col-md-2 pl-0">' +
            '    <button class="btn btn-default btn-block btn-new-patient" ' +
            '            type="button" ' +
            '            id="patient-' + label + '-button">' +
            '      <span id="patient-' + label + '-symbol" class="fas ' + symbol + '"></span>' +
            '    </button>' +
            '  </div>' +
            '</div>'
        );

    }

    addBlankPatientForm(index) {

        this.addPatientForm(index, { id: -1, name: '', age: '' }, 'fa-plus');

        // bind addBlankPatientForm to click
        this.placeholder.find('#patient-' + this.label + '-' + index + '-button')
            .off('click')
            .on('click', () => {

                this.addBlankPatientForm(index + 1);

            });

    }

    removePatientForm(index) {

        // remove from form
        this.placeholder
            .find('#patient-' + this.label + '-' + index + '-form')
            .hide();

    }

    addPatientForm(index, patient, symbol = 'fa-minus') {

        // add to form
        this.placeholder.append(Patients.patientForm(this.label + '-' + index, symbol, patient));

        // bind remove action
        this.placeholder.find('#patient-' + this.label + '-' + index + '-button')
            .on('click', () => { this.removePatientForm(index); });

    }

    createForm() {

        // add existing patients
        let index = 0;
        this.patients.forEach( (patient) => {

            index += 1;
            this.addPatientForm(index, patient);

        });

        // add blank form
        index += 1;
        this.addBlankPatientForm(index);

    }

}