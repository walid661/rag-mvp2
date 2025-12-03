

"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { userProfileSchema, UserProfileInput } from '../lib/zod';

/**
 * ProfileForm collects onboarding information from the user. Upon successful
 * submission it persists the profile via the `/api/profile` endpoint and
 * redirects to the chat page. Basic client-side validation is performed
 * using Zod.
 */
export default function ProfileForm() {
  const router = useRouter();
  const [form, setForm] = useState<UserProfileInput>({
    age: undefined,
    sexe: undefined,
    niveau_sportif: undefined,
    objectif_principal: undefined,
    frequence_hebdo: undefined,
    temps_disponible: undefined,
    materiel_disponible: [],
    zones_ciblees: [],
    contraintes_physiques: [],
    preferences: { style: '' },
    experience_precedente: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: async (profile: UserProfileInput) => {
      const res = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    },
    onSuccess: () => {
      router.push('/chat');
    },
  });

  const handleChange = (field: keyof UserProfileInput, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleArrayToggle = (field: keyof UserProfileInput, option: string) => {
    setForm((prev) => {
      const current = (prev[field] as string[]) || [];
      const exists = current.includes(option);
      const next = exists ? current.filter((o) => o !== option) : [...current, option];
      return { ...prev, [field]: next };
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Validate with Zod
    const parsed = userProfileSchema.safeParse(form);
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      parsed.error.errors.forEach((err) => {
        const key = err.path.join('.') || err.code;
        fieldErrors[key] = err.message;
      });
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    mutation.mutate(form);
  };

  const materialOptions = ['Tapis de sol', 'Haltères', 'Élastiques', 'Kettlebell', 'Aucun'];
  const zoneOptions = ['Haut du corps', 'Bas du corps', 'Full body', 'Abdominaux'];
  const contraintesOptions = ['Aucune', 'Genou', 'Épaule', 'Dos'];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium">Âge</label>
          <input
            type="number"
            value={form.age ?? ''}
            onChange={(e) => handleChange('age', e.target.value === '' ? undefined : Number(e.target.value))}
            className="mt-1 w-full p-2 border rounded-md"
          />
          {errors.age && <p className="text-red-500 text-sm">{errors.age}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium">Sexe</label>
          <select
            value={form.sexe ?? ''}
            onChange={(e) => handleChange('sexe', e.target.value as any || undefined)}
            className="mt-1 w-full p-2 border rounded-md"
          >
            <option value="">--</option>
            <option value="Homme">Homme</option>
            <option value="Femme">Femme</option>
            <option value="Autre">Autre</option>
          </select>
          {errors.sexe && <p className="text-red-500 text-sm">{errors.sexe}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium">Niveau sportif</label>
          <select
            value={form.niveau_sportif ?? ''}
            onChange={(e) => handleChange('niveau_sportif', e.target.value as any || undefined)}
            className="mt-1 w-full p-2 border rounded-md"
          >
            <option value="">--</option>
            <option value="Débutant">Débutant</option>
            <option value="Intermédiaire">Intermédiaire</option>
            <option value="Avancé">Avancé</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Objectif principal</label>
          <select
            value={form.objectif_principal ?? ''}
            onChange={(e) => handleChange('objectif_principal', e.target.value as any || undefined)}
            className="mt-1 w-full p-2 border rounded-md"
          >
            <option value="">--</option>
            <option value="Perte de poids">Perte de poids</option>
            <option value="Prise de muscle">Prise de muscle</option>
            <option value="Mobilité">Mobilité</option>
            <option value="Endurance">Endurance</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Fréquence hebdomadaire (séances/semaine)</label>
          <input
            type="number"
            value={form.frequence_hebdo ?? ''}
            onChange={(e) => handleChange('frequence_hebdo', e.target.value === '' ? undefined : Number(e.target.value))}
            className="mt-1 w-full p-2 border rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Temps disponible par séance (minutes)</label>
          <input
            type="number"
            value={form.temps_disponible ?? ''}
            onChange={(e) => handleChange('temps_disponible', e.target.value === '' ? undefined : Number(e.target.value))}
            className="mt-1 w-full p-2 border rounded-md"
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Matériel disponible</label>
        <div className="flex flex-wrap gap-2">
          {materialOptions.map((opt) => (
            <label key={opt} className="flex items-center space-x-1">
              <input
                type="checkbox"
                checked={form.materiel_disponible?.includes(opt)}
                onChange={() => handleArrayToggle('materiel_disponible', opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Zones ciblées</label>
        <div className="flex flex-wrap gap-2">
          {zoneOptions.map((opt) => (
            <label key={opt} className="flex items-center space-x-1">
              <input
                type="checkbox"
                checked={form.zones_ciblees?.includes(opt)}
                onChange={() => handleArrayToggle('zones_ciblees', opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Contraintes physiques</label>
        <div className="flex flex-wrap gap-2">
          {contraintesOptions.map((opt) => (
            <label key={opt} className="flex items-center space-x-1">
              <input
                type="checkbox"
                checked={form.contraintes_physiques?.includes(opt)}
                onChange={() => handleArrayToggle('contraintes_physiques', opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium">Style d'entraînement préféré</label>
        <input
          type="text"
          value={form.preferences?.style ?? ''}
          onChange={(e) => setForm((prev) => ({ ...prev, preferences: { ...prev.preferences, style: e.target.value } }))}
          className="mt-1 w-full p-2 border rounded-md"
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Expérience précédente</label>
        <textarea
          value={form.experience_precedente ?? ''}
          onChange={(e) => handleChange('experience_precedente', e.target.value)}
          className="mt-1 w-full p-2 border rounded-md"
          rows={3}
        />
      </div>
      <button
        type="submit"
        disabled={mutation.isPending}
        className="mt-4 px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 disabled:opacity-50"
      >
        {mutation.isPending ? 'Enregistrement...' : 'Enregistrer et continuer'}
      </button>
      {mutation.error && <p className="text-red-500 mt-2">{String(mutation.error)}</p>}
    </form>
  );
}