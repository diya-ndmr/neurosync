import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface Appointment {
  id: string;
  student_id: string;
  status: string;
  starts_at: string;
  duration_minutes: number;
  location: string;
  follow_up: string | null;
}
interface Slot {
  id: string;
  starts_at: string;
  duration_minutes: number;
  location: string;
  active: boolean;
  booked: boolean;
}
interface Referral {
  id: string;
  student_id: string;
  student_name: string;
  status: string;
  created_at: string;
}

export default function WellnessAppointments() {
  const { token } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [startsAt, setStartsAt] = useState('');
  const [duration, setDuration] = useState(30);
  const [location, setLocation] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadAppointments = async () => {
    if (!token) return;
    const [appointmentRows, slotRows, referralRows] = await Promise.all([
      api.get<Appointment[]>('/wellbeing/appointments', token),
      api.get<Slot[]>('/wellbeing/slots/manage', token),
      api.get<Referral[]>('/wellbeing/referrals', token)
    ]);
    setAppointments(appointmentRows);
    setSlots(slotRows);
    setReferrals(referralRows);
  };

  useEffect(() => {
    loadAppointments().catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Appointments could not be loaded.'));
  }, [token]);

  const createSlot = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.post('/wellbeing/slots', {
        starts_at: new Date(startsAt).toISOString(),
        duration_minutes: duration,
        location
      }, token);
      setNotice('Appointment slot added to NeuroSync.');
      setStartsAt('');
      setLocation('');
      await loadAppointments();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Appointment slot could not be created.');
    } finally {
      setSaving(false);
    }
  };

  const updateSlot = async (slot: Slot) => {
    if (!token) return;
    setError(null);
    try {
      await api.patch(`/wellbeing/slots/${slot.id}`, { active: !slot.active }, token);
      await loadAppointments();
      setNotice('Appointment slot availability updated.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Slot availability could not be updated.');
    }
  };

  const updateReferral = async (referral: Referral) => {
    if (!token) return;
    setError(null);
    try {
      await api.patch(`/wellbeing/referrals/${referral.id}`, { status: referral.status === 'active' ? 'closed' : 'active' }, token);
      await loadAppointments();
      setNotice('Wellness recommendation status updated.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Recommendation status could not be updated.');
    }
  };

  const updateAppointment = async (appointmentId: string, status: 'cancelled' | 'completed' | 'follow_up') => {
    if (!token) return;
    const followUp = status === 'follow_up' ? window.prompt('Enter a brief support coordination follow-up (do not include counselling notes):') : null;
    if (status === 'follow_up' && followUp === null) return;
    setError(null);
    try {
      await api.patch(`/wellbeing/appointments/${appointmentId}`, { status, follow_up: followUp }, token);
      await loadAppointments();
      setNotice('Appointment status updated.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Appointment could not be updated.');
    }
  };

  return <div className="space-y-5">
    <header className="neo-card p-6"><h1 className="text-2xl font-bold text-ink">Wellness appointments</h1><p className="mt-1 text-sm text-ink-soft">Manage appointment availability and coordination follow-ups. Counselling records are not stored in NeuroSync.</p></header>
    {error && <p role="alert" className="text-sm text-ns-danger">{error}</p>}
    {notice && <p role="status" className="text-sm text-ns-success">{notice}</p>}
    <form onSubmit={(event) => void createSlot(event)} className="neo-card grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
      <label className="text-sm">Appointment date and time<input className="neo-input mt-1" type="datetime-local" required value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label>
      <label className="text-sm">Duration<select className="neo-input mt-1" value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value={30}>30 minutes</option><option value={45}>45 minutes</option><option value={60}>60 minutes</option><option value={90}>90 minutes</option></select></label>
      <label className="text-sm">Location or meeting details<input className="neo-input mt-1" required maxLength={200} value={location} onChange={(event) => setLocation(event.target.value)} /></label>
      <button className="neo-btn self-end px-4 py-2.5 text-sm" disabled={saving}>{saving ? 'Saving…' : 'Add available slot'}</button>
    </form>
    <section className="neo-card p-5"><h2 className="mb-3 font-semibold">Appointment slot availability</h2>{slots.length === 0 ? <p className="text-sm text-ink-faint">No slots have been configured.</p> : <div className="space-y-2">{slots.map((slot) => <div key={slot.id} className="flex flex-wrap items-center justify-between gap-3 border border-ns-border p-3"><p className="text-sm">{new Date(slot.starts_at).toLocaleString()} · {slot.duration_minutes} min · {slot.location} · {slot.booked ? 'Booked' : slot.active ? 'Available' : 'Inactive'}</p><button type="button" disabled={slot.booked && slot.active} onClick={() => void updateSlot(slot)} className="rounded border border-ns-border px-3 py-2 text-xs">{slot.active ? 'Deactivate slot' : 'Activate slot'}</button></div>)}</div>}</section>
    <section className="neo-card p-5"><h2 className="mb-3 font-semibold">Support recommendations</h2>{referrals.length === 0 ? <p className="text-sm text-ink-faint">No Wellness recommendations have been made.</p> : <div className="space-y-2">{referrals.map((referral) => <div key={referral.id} className="flex flex-wrap items-center justify-between gap-3 border border-ns-border p-3"><p className="text-sm">{referral.student_name} · {referral.student_id} · <span className="capitalize">{referral.status}</span></p><button type="button" onClick={() => void updateReferral(referral)} className="rounded border border-ns-border px-3 py-2 text-xs">{referral.status === 'active' ? 'Close recommendation' : 'Reopen recommendation'}</button></div>)}</div>}</section>
    <section className="neo-card p-5"><h2 className="mb-3 font-semibold">Bookings and follow-ups</h2>{appointments.length === 0 ? <p className="text-sm text-ink-faint">No bookings have been made.</p> : <div className="space-y-3">{appointments.map((appointment) => <article key={appointment.id} className="flex flex-wrap items-center justify-between gap-3 border border-ns-border p-4"><div><p className="font-medium">{new Date(appointment.starts_at).toLocaleString()} · {appointment.duration_minutes} minutes</p><p className="text-sm text-ink-soft">Student record: {appointment.student_id} · {appointment.location} · <span className="capitalize">{appointment.status.replace('_', ' ')}</span></p>{appointment.follow_up && <p className="mt-1 text-sm">Follow-up: {appointment.follow_up}</p>}</div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => void updateAppointment(appointment.id, 'follow_up')} className="rounded border border-ns-border px-3 py-2 text-xs">Add follow-up</button><button type="button" onClick={() => void updateAppointment(appointment.id, 'completed')} className="rounded border border-ns-border px-3 py-2 text-xs">Mark completed</button>{appointment.status !== 'cancelled' && <button type="button" onClick={() => void updateAppointment(appointment.id, 'cancelled')} className="rounded border border-ns-border px-3 py-2 text-xs">Cancel</button>}</div></article>)}</div>}</section>
  </div>;
}
