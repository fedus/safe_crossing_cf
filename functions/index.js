const functions = require('firebase-functions');

const admin = require('firebase-admin');

admin.initializeApp();

const db = admin.firestore();

const nodeIdToFirestoreId = (nodeId) => nodeId.split('/')[1];

exports.initializeUser = functions
    .region('europe-west1')
    .https
    .onCall(async (data, context) => {
      const {userUuid} = data;

      const userDoc = await db.collection('users').doc(userUuid).get();

      if (userDoc.exists && userDoc.get('initialized')) {
        return Promise.resolve('USER_ALREADY_INITIALIZED');
      }

      const allCrossings = await db.collection('crossings').get();

      let batch = db.batch();
      let index = 0;

      functions.logger.log(`Initializing user ${userUuid}`);

      for (const currentCrossing of allCrossings.docs) {
        functions.logger.log(`Working off ${currentCrossing.id}`);
        batch.update(currentCrossing.ref, {
          'unseenBy': admin.firestore.FieldValue.arrayUnion(userUuid),
        });

        if ((index + 1) % 498 == 0) {
          functions.logger.log(`Committing intermediate batch at index $index`);
          await batch.commit();
          batch = db.batch();
        }

        index++;
      }

      batch.set(userDoc.ref, {initialized: true}, {merge: true});

      functions.logger.log('Committing user eligibility ...');
      await batch.commit();

      return Promise.resolve('USER_INITIALIZED');
    });

exports.vote = functions
    .region('europe-west1')
    .https
    .onCall((data, context) => {
      const {userUuid, crossingNodeId, vote} = data;

      const voteEnumIndextoString = ['CANT_SAY', 'OK', 'PARKING_CLOSE'];
      const voteEnumIndextoFirestoreProperty = [
        'votesNotSure',
        'votesOk',
        'votesTooClose',
      ];

      functions
          .logger
          .log(
              `User ${userUuid} voting for \
              ${crossingNodeId} with ${vote} \
              (${voteEnumIndextoString[vote]})`,
          );

      const crossingRef = db.collection('crossings')
          .doc(crossingNodeId.split('/')[1]);

      const voteRef = crossingRef
          .collection('votes')
          .doc(userUuid);

      const metaDoc = db.collection('meta').doc('meta');

      return db.runTransaction(async (transaction) => {
        const voteSnapshot = await voteRef.get();
        const crossingSnapshot = await crossingRef.get();
        const totalVotesForCrossing = crossingSnapshot.get('votesTotal');

        if (voteSnapshot.exists) {
          const existingVote = voteSnapshot.get('vote');

          if (existingVote != vote) {
            transaction.update(crossingRef, {
              [voteEnumIndextoFirestoreProperty[existingVote]]: admin
                  .firestore
                  .FieldValue
                  .increment(-1),
              [voteEnumIndextoFirestoreProperty[vote]]: admin
                  .firestore
                  .FieldValue
                  .increment(1),
            });
          }
        } else {
          transaction.update(crossingRef, {
            [voteEnumIndextoFirestoreProperty[vote]]: admin
                .firestore
                .FieldValue
                .increment(1),
            'votesTotal': admin.firestore.FieldValue.increment(1),
            'unseenBy': admin.firestore.FieldValue.arrayRemove(userUuid),
          });

          if (totalVotesForCrossing == 4) { // 5th vote was just cast
            transaction.update(metaDoc, {
              crossingsWithEnoughVotes: admin.firestore.FieldValue.increment(1),
            });
          }
        }

        transaction.set(voteRef, {vote});
      })
          .then((value) => 'Vote cast')
          .catch((error) => `Failed to cast vote: ${error}`);
    });

exports.getNextBatch = functions
    .region('europe-west1')
    .https
    .onCall(async (data, context) => {
      const {userId, quantity, lastCrossingId} = data;

      functions
          .logger
          .log(
              `Getting next batch of ${quantity} crossings for \
              ${userId}, last crossing id \
              ${lastCrossingId ? lastCrossingId : 'n/a'}`,
          );

      const crossingsCollection = db.collection('crossings');

      let crossingQuery;

      if (lastCrossingId) {
        const lastCrossingFirebaseId = nodeIdToFirestoreId(lastCrossingId);

        const lastCrossingReference = await crossingsCollection
            .doc(lastCrossingFirebaseId)
            .get();

        crossingQuery = crossingsCollection
            .where('unseenBy', 'array-contains', userId)
            .orderBy('votesTotal')
            .startAfter(lastCrossingReference);
      } else {
        crossingQuery = crossingsCollection
            .where('unseenBy', 'array-contains', userId)
            .orderBy('votesTotal');
      }

      const _crossingsQuerySnapshot = await crossingQuery
          .limit(quantity)
          .get();

      return _crossingsQuerySnapshot.docs.map((crossingDocument) =>
        crossingDocument.data());
    });
