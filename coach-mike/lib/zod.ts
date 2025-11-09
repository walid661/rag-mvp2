import { z } from 'zod';

/**
 * Zod schema for validating the user profile data in the onboarding form.
 * All fields are optional to allow partial completion, but enumerated
 * constraints are enforced where appropriate. Additional preferences are
 * captured in the preferences object.
 */
export const userProfileSchema = z.object({
  age: z
    .number({ invalid_type_error: 'L\'âge doit être un nombre' })
    .int('L\'âge doit être un entier')
    .min(0, { message: 'Âge invalide' })
    .max(120, { message: 'Âge invalide' })
    .optional(),
  sexe: z.enum(['Homme', 'Femme', 'Autre']).optional(),
  niveau_sportif: z.enum(['Débutant', 'Intermédiaire', 'Avancé']).optional(),
  objectif_principal: z.enum(['Perte de poids', 'Prise de muscle', 'Mobilité', 'Endurance']).optional(),
  frequence_hebdo: z
    .number({ invalid_type_error: 'La fréquence doit être un nombre' })
    .int()
    .min(1)
    .max(14)
    .optional(),
  temps_disponible: z
    .number({ invalid_type_error: 'Le temps doit être un nombre' })
    .int()
    .min(1)
    .max(300)
    .optional(),
  materiel_disponible: z.array(z.string()).optional(),
  zones_ciblees: z.array(z.string()).optional(),
  contraintes_physiques: z.array(z.string()).optional(),
  preferences: z.record(z.any()).optional(),
  experience_precedente: z.string().optional(),
});

export type UserProfileInput = z.infer<typeof userProfileSchema>;