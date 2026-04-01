const SENSOR_ID = 'cd0f6886-6a12-4b0d-a894-7a7513e2ac3f';
const STECKDOSE_ID = '3f0fc7e2-680c-412f-a850-659b82b721dd';
const LICHT_SCHWELLE = 50;
const ZEIT_VON = 6;
const ZEIT_BIS = 16;
const ABWESENHEIT_MIN = 5;

const stunde = new Date().getHours();
const zeitOk = stunde >= ZEIT_VON && stunde < ZEIT_BIS;
const jetzt = Date.now();

const bewegung = await Homey.devices.getCapabilityValue({ deviceId: SENSOR_ID, capabilityId: 'alarm_motion' });
const helligkeit = await Homey.devices.getCapabilityValue({ deviceId: SENSOR_ID, capabilityId: 'measure_luminance' });

log('Bewegung: ' + bewegung + ' | Helligkeit: ' + helligkeit + ' lux | Zeitfenster: ' + zeitOk);

if (bewegung) {
  global.buero_letzte_bewegung = jetzt;
  log('Zeitstempel gesetzt: ' + new Date(jetzt).toLocaleTimeString());

  if (!zeitOk) {
    log('Ausserhalb Zeitfenster, kein Einschalten');
  } else if (helligkeit !== null && helligkeit >= LICHT_SCHWELLE) {
    log('Tageslicht reicht (' + helligkeit + ' lux), kein Einschalten');
  } else {
    log('Zu dunkel (' + helligkeit + ' lux), Steckdose EIN');
    await Homey.devices.setCapabilityValue({ deviceId: STECKDOSE_ID, capabilityId: 'onoff', value: true });
  }

} else {
  const letzteBewegung = global.buero_letzte_bewegung || null;

  if (!letzteBewegung) {
    log('Kein Zeitstempel, Steckdose AUS');
    await Homey.devices.setCapabilityValue({ deviceId: STECKDOSE_ID, capabilityId: 'onoff', value: false });
  } else {
    const minuten = (jetzt - letzteBewegung) / 1000 / 60;
    log('Letzte Bewegung vor ' + minuten.toFixed(1) + ' Min (Schwelle: ' + ABWESENHEIT_MIN + ' Min)');

    if (minuten >= ABWESENHEIT_MIN) {
      log('Timer abgelaufen, Steckdose AUS');
      await Homey.devices.setCapabilityValue({ deviceId: STECKDOSE_ID, capabilityId: 'onoff', value: false });
      global.buero_letzte_bewegung = null;
    } else {
      log('Timer laeuft noch, Steckdose bleibt an');
    }
  }
}
