import api from '@/api'

/**
 * Télécharge un fichier servi par une route protégée.
 *
 * Un simple lien ne conviendrait pas : le jeton voyage dans l'en-tête
 * Authorization, que le navigateur n'ajoute pas à une navigation directe.
 * On récupère donc le corps en blob avant de déclencher l'enregistrement.
 */
export async function telechargerFichier(url: string, nomParDefaut: string) {
  const reponse = await api.get(url, { responseType: 'blob' })

  const entete = reponse.headers['content-disposition'] as string | undefined
  const trouve = entete?.match(/filename="?([^";]+)"?/)
  const nom = trouve?.[1] ?? nomParDefaut

  const lienObjet = URL.createObjectURL(reponse.data as Blob)
  const lien = document.createElement('a')
  lien.href = lienObjet
  lien.download = nom
  document.body.appendChild(lien)
  lien.click()
  document.body.removeChild(lien)
  URL.revokeObjectURL(lienObjet)
}
