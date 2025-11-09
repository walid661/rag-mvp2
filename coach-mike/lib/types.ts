/**
 * Shared TypeScript definitions for the Coach Mike app.
 * These mirror the backend API contract. Keeping them here allows both
 * client-side and server-side code to import a single source of truth.
 */

export type UserProfile = {
  age?: number;
  sexe?: 'Homme' | 'Femme' | 'Autre';
  niveau_sportif?: 'Débutant' | 'Intermédiaire' | 'Avancé';
  objectif_principal?: 'Perte de poids' | 'Prise de muscle' | 'Mobilité' | 'Endurance';
  frequence_hebdo?: number;
  temps_disponible?: number;
  materiel_disponible?: string[];
  zones_ciblees?: string[];
  contraintes_physiques?: string[];
  preferences?: { style?: string; [k: string]: unknown };
  experience_precedente?: string;
};

export type ChatRequest = {
  query: string;
  profile: UserProfile;
};

export type ChatResponse = {
  answer: string;
  sources: Array<Record<string, any>>;
};