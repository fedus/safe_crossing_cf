const functions = require('firebase-functions');

const admin = require('firebase-admin');

admin.initializeApp();

const db = admin.firestore();

exports.initializeUser = functions
    .region('europe-west1')
    .https
    .onRequest(async (req, res) => {
      const {userUuid} = req.query;

      let batch = db.batch();

      const allCrossings = await db.collection('crossings').get();

      let index = 0;

      functions.logger.log(`Initializing user ${userUuid}`);

      for (const currentCrossing of allCrossings.docs) {
        functions.logger.log(`Working off ${currentCrossing.id}`);
        batch.update(currentCrossing._ref, {
          'unseenBy': admin.firestore.FieldValue.arrayUnion(userUuid),
        });

        if ((index + 1) % 499 == 0) {
          functions.logger.log(`Committing intermediate batch at index $index`);
          await batch.commit();
          batch = db.batch();
        }

        index++;
      }

      functions.logger.log('Committing user eligibility ...');
      await batch.commit();

      res.status(200).send('OK');
    });
